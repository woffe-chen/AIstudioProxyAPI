import json
import logging
import re
import zlib
import time

class HttpInterceptor:
    """
    Class to intercept and process HTTP requests and responses
    """
    def __init__(self, log_dir='logs'):
        self.log_dir = log_dir
        self.logger = logging.getLogger('http_interceptor')
        self.setup_logging()

        # 流式缓冲状态管理
        self._tool_call_buffer = ""      # 缓冲可能的 tool call 内容
        self._is_buffering = False       # 是否正在缓冲
        self._buffer_start_marker = "```json"  # 开始标记
        self._buffer_end_marker = "```"  # 结束标记
        self._buffer_timeout = 2.0       # 2秒超时（从5秒缩短，避免VSCode认为无响应）
        self._buffer_start_time = None   # 缓冲开始时间
        self._keepalive_count = 0        # 保活消息计数器（用于周期性保活）

        # 统计模式计数器（用于诊断数据丢失）
        self._parse_call_count = 0        # parse_response 调用次数
        self._total_body_extracted = 0    # 从 Gemini API 提取的总字节数
        self._total_body_sent = 0         # 发送给客户端的总字节数
    
    @staticmethod
    def setup_logging():
        """Set up logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
        logging.getLogger('asyncio').setLevel(logging.ERROR)
        logging.getLogger('websockets').setLevel(logging.ERROR)
    
    @staticmethod
    def should_intercept(host, path):
        """
        Determine if the request should be intercepted based on host and path
        """
        # Check if the endpoint contains GenerateContent
        if 'GenerateContent' in path:
            return True
        
        # Add more conditions as needed
        return False
    
    async def process_request(self, request_data, host, path):
        """
        Process the request data before sending to the server
        """
        if not self.should_intercept(host, path):
            return request_data
        
        # Log the request
        self.logger.info(f"Intercepted request to {host}{path}")
        
        try:
            return request_data
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Not JSON or not UTF-8, just pass through
            return request_data
    
    async def process_response(self, response_data, host, path, headers):
        """
        Process the response data before sending to the client
        """
        # 【重要】添加 INFO 日志跟踪调用
        if self._parse_call_count == 0:  # 首次调用
            self.logger.info(f"[DEBUG] process_response 首次被调用，数据长度: {len(response_data)}")

        try:
            # Handle chunked encoding
            decoded_data, is_done = self._decode_chunked(bytes(response_data))
            # Handle gzip encoding
            decoded_data = self._decompress_zlib_stream(decoded_data)
            result  = self.parse_response(decoded_data)
            result["done"] = is_done

            # 在响应结束时重置缓冲状态
            if is_done:
                self._reset_buffer_state()
                self.logger.info("[DEBUG] 响应完成，重置缓冲状态")

            return result
        except Exception as e:
            self.logger.error(f"[DEBUG] process_response 发生异常: {e}")
            raise e

    def parse_response(self, response_data):
        # 统计调用次数
        self._parse_call_count += 1

        # 【原始数据捕获】记录 Gemini API 返回的原始数据
        # 使用 [RAW_RESPONSE] 标记以便后续分析工具提取
        if response_data:
            self.logger.info(f"[RAW_RESPONSE] chunk_{self._parse_call_count}: {response_data}")

        # 【重要】添加 INFO 级别日志以确认方法被调用
        if self._parse_call_count == 1:
            self.logger.info(f"[DEBUG] parse_response 首次被调用，数据长度: {len(response_data) if response_data else 0}")

        # 添加诊断日志
        if response_data:
            self.logger.debug(f"parse_response: 接收到 {len(response_data)} 字节数据")
            self.logger.debug(f"parse_response: 数据前 200 字节: {response_data[:200]}")

        pattern = rb'\[\[\[null,.*?],\"model\"]]'
        matches = []
        for match_obj in re.finditer(pattern, response_data):
            matches.append(match_obj.group(0))

        self.logger.debug(f"parse_response: 正则匹配到 {len(matches)} 个 JSON 块")

        # 【诊断】如果正则匹配到数据但后续解析失败，记录原始数据
        if len(matches) > 0 and self._parse_call_count <= 5:
            self.logger.info(f"[诊断] 匹配到 {len(matches)} 个块，第一个块长度: {len(matches[0])}, 前100字节: {matches[0][:100]}")


        resp = {
            "reason": "",
            "body": "",
            "function": [],
        }

        # Print each full match
        for match in matches:
            try:
                # 【修复】使用 strict=False 允许解析包含未转义换行符的 JSON
                # Gemini API 返回的 JSON 字符串中可能包含原始换行符，这是技术上无效的 JSON
                # 但使用 strict=False 可以容忍这些格式问题
                json_data = json.loads(match, strict=False)
            except json.JSONDecodeError as je:
                # JSON 解析失败（可能是 Extra data 错误），跳过这个块
                self.logger.debug(f"跳过无效的 JSON 块 (JSONDecodeError at pos {je.pos}): {match[:100]}")
                continue
            except Exception as e:
                # 其他解析错误
                self.logger.debug(f"JSON 解析遇到异常: {e}, 跳过该块")
                continue

            try:
                payload = json_data[0][0]
            except Exception as e:
                # 【诊断】记录 payload 提取失败
                self.logger.debug(f"Payload 提取失败: {e}, json_data 结构: {type(json_data)}, 长度: {len(json_data) if hasattr(json_data, '__len__') else 'N/A'}")
                if isinstance(json_data, list) and len(json_data) > 0:
                    self.logger.debug(f"json_data[0] 类型: {type(json_data[0])}, 长度: {len(json_data[0]) if hasattr(json_data[0], '__len__') else 'N/A'}")
                continue

            if len(payload)==2: # body
                resp["body"] = resp["body"] + payload[1]
            elif len(payload) == 11 and payload[1] is None and type(payload[10]) == list:  # function
                array_tool_calls = payload[10]
                func_name = array_tool_calls[0]
                params = self.parse_toolcall_params(array_tool_calls[1])
                resp["function"].append({"name":func_name, "params":params})
            elif len(payload) > 2: # reason
                resp["reason"] = resp["reason"] + payload[1]

        # 统计从 Gemini API 提取的 body 字节数
        if resp["body"]:
            original_body_size = len(resp["body"])
            self._total_body_extracted += original_body_size
            self.logger.debug(f"[统计] 本次提取 body: {original_body_size} 字节")

        # ---------------------------------------------------------
        # [第三版] 伪函数调用拦截器 (Pseudo-Function Calling Interceptor)
        # 采用检测-缓冲-周期性保活模式（Detect-Buffer-Keepalive Pattern）
        # 核心改进：
        # 1. 状态 A: 直接发送模式 - 支持跨 chunk 检测 ```json 标记
        # 2. 状态 B: JSON缓冲 + 周期性保活（每 0.5 秒）
        # 3. 状态 C: 发送 tool use + 后续内容
        # ---------------------------------------------------------
        if resp["body"]:
            # 将新内容添加到缓冲区
            self._tool_call_buffer += resp["body"]

            # === 状态 A：直接发送模式 ===
            # 检测是否出现 ```json 标记
            if not self._is_buffering and self._buffer_start_marker in self._tool_call_buffer:
                # 找到开始标记的位置
                idx = self._tool_call_buffer.find(self._buffer_start_marker)
                before_marker = self._tool_call_buffer[:idx]

                # 【渐进式发送】立即发送标记之前的所有内容
                if before_marker.strip():
                    self.logger.debug(f"检测到 tool call 开始标记，发送前置内容: {repr(before_marker[:50])}")
                    resp["body"] = before_marker
                    self._tool_call_buffer = self._tool_call_buffer[idx:]

                    # 转换到状态 B
                    self._is_buffering = True
                    self._buffer_start_time = time.time()
                    self._keepalive_count = 0
                    return resp
                else:
                    # 如果前面没有内容，直接进入缓冲模式
                    self.logger.debug("检测到 tool call 开始标记（无前置内容），进入缓冲模式")
                    self._tool_call_buffer = self._tool_call_buffer[idx:]

                    # 转换到状态 B
                    self._is_buffering = True
                    self._buffer_start_time = time.time()
                    self._keepalive_count = 0

            # === 状态 B：JSON缓冲 + 周期性保活模式 ===
            if self._is_buffering:
                # 检查超时保护
                elapsed = time.time() - self._buffer_start_time
                if elapsed > self._buffer_timeout:
                    self.logger.warning("Tool call 缓冲超时，强制释放")
                    resp["body"] = self._tool_call_buffer
                    self._reset_buffer_state()
                    return resp

                # 尝试匹配完整的 tool call 块
                tc_pattern = r'```json\s*(\{.*?"tool_call":.*?\})\s*```'
                tc_match = re.search(tc_pattern, self._tool_call_buffer, re.DOTALL)

                if tc_match:
                    # === 状态 C：发送 tool use + 后续内容 ===
                    json_str = tc_match.group(1)
                    try:
                        # 【修复】使用 strict=False 以兼容 Gemini 返回的格式
                        tool_payload = json.loads(json_str, strict=False)
                        if "tool_call" in tool_payload:
                            tc_data = tool_payload["tool_call"]
                            func_name = tc_data.get("name")
                            func_args = tc_data.get("arguments", {})

                            if func_name:
                                # 提取函数调用到 function 列表
                                resp["function"].append({
                                    "name": func_name,
                                    "params": func_args
                                })
                                self.logger.info(f"成功解析 tool call: {func_name}")

                        # 【渐进式发送】发送 JSON 之后的内容
                        after_json = self._tool_call_buffer.replace(tc_match.group(0), "")
                        if after_json.strip():
                            self.logger.debug(f"Tool call 解析完成，发送后续内容: {repr(after_json[:50])}")
                            resp["body"] = after_json
                        else:
                            resp["body"] = ""

                        # 重置状态，回到状态 A
                        self._tool_call_buffer = ""
                        self._is_buffering = False
                        self._buffer_start_time = None
                        self._keepalive_count = 0
                        return resp

                    except json.JSONDecodeError:
                        # JSON 不完整，继续缓冲
                        self.logger.debug("JSON 尚未完整，继续缓冲")
                        pass

                # JSON 未完成，发送周期性保活
                keepalive_interval = 0.5  # 每 0.5 秒发送一次
                if elapsed > (self._keepalive_count + 1) * keepalive_interval:
                    self.logger.debug(f"发送周期性保活 #{self._keepalive_count + 1}")
                    resp["body"] = "[正在调用工具...]\n"
                    self._keepalive_count += 1
                    return resp
                else:
                    # 这次不发送保活，返回空 body
                    resp["body"] = ""
                    return resp

            else:
                # === 状态 A（继续）：没有检测到标记，正常发送 ===
                # 【修复方案】更精确的检测条件：
                # 只有当缓冲区中已经包含完整的 ```json 标记时才考虑缓冲
                # 这避免了短 chunk 被过度缓冲的问题

                # 检查是否已经有部分 ```json 标记（支持跨 chunk 检测）
                # 但不会因为普通的 ` 或 tool_call 字符串就阻塞数据
                has_partial_marker = (
                    self._tool_call_buffer.endswith(('`', '``', '```', '```j', '```js', '```jso'))
                )

                if has_partial_marker and len(self._tool_call_buffer) <= 10:
                    # 可能正在接收 ```json 标记的开头，但缓冲区很短
                    # 保留这些内容，等待下一个 chunk
                    self.logger.debug(f"检测到可能的标记前缀，保留缓冲区 ({len(self._tool_call_buffer)} 字节)")
                    resp["body"] = ""
                else:
                    # 其他情况：立即发送所有内容
                    # 包括：
                    # 1. 没有部分标记
                    # 2. 有部分标记但缓冲区已经很长（>10字节），说明不是真正的标记前缀
                    resp["body"] = self._tool_call_buffer
                    self._tool_call_buffer = ""
                    if resp["body"]:
                        self.logger.debug(f"没有检测到 ```json 标记，发送所有内容: {len(resp['body'])} 字节")
        # ---------------------------------------------------------

        # 统计实际发送的 body 字节数
        final_body_size = len(resp["body"])
        self._total_body_sent += final_body_size
        if final_body_size > 0:
            self.logger.debug(f"[统计] 本次发送 body: {final_body_size} 字节")

        # 每 10 次调用输出一次统计汇总
        if self._parse_call_count % 10 == 0:
            buffer_size = len(self._tool_call_buffer)
            self.logger.info(
                f"[统计] 调用: {self._parse_call_count} 次, "
                f"提取: {self._total_body_extracted} 字节, "
                f"发送: {self._total_body_sent} 字节, "
                f"缓冲区: {buffer_size} 字节"
            )

        return resp

    def _reset_buffer_state(self):
        """重置缓冲状态（在响应结束时调用）"""
        # 输出最终统计
        if self._parse_call_count > 0:
            data_loss = self._total_body_extracted - self._total_body_sent
            loss_percentage = (data_loss / max(self._total_body_extracted, 1)) * 100
            self.logger.info(
                f"[最终统计] 总调用: {self._parse_call_count}, "
                f"总提取: {self._total_body_extracted} 字节, "
                f"总发送: {self._total_body_sent} 字节, "
                f"丢失: {data_loss} 字节 ({loss_percentage:.1f}%)"
            )

        # 重置所有状态
        self._tool_call_buffer = ""
        self._is_buffering = False
        self._buffer_start_time = None
        self._keepalive_count = 0

        # 重置统计计数器
        self._parse_call_count = 0
        self._total_body_extracted = 0
        self._total_body_sent = 0

    def parse_toolcall_params(self, args):
        try:
            params = args[0]
            func_params = {}
            for param in params:
                param_name = param[0]
                param_value = param[1]

                if type(param_value)==list:
                    if len(param_value)==1: # null
                        func_params[param_name] = None
                    elif len(param_value) == 2: # number and integer
                        func_params[param_name] = param_value[1]
                    elif len(param_value) == 3: # string
                        func_params[param_name] = param_value[2]
                    elif len(param_value) == 4: # boolean
                        func_params[param_name] = param_value[3] == 1
                    elif len(param_value) == 5: # object
                        func_params[param_name] = self.parse_toolcall_params(param_value[4])
            return func_params
        except Exception as e:
            raise e

    @staticmethod
    def _decompress_zlib_stream(compressed_stream):
        decompressor = zlib.decompressobj(wbits=zlib.MAX_WBITS | 32)  # zlib header
        decompressed = decompressor.decompress(compressed_stream)
        return decompressed

    @staticmethod
    def _decode_chunked(response_body: bytes) -> tuple[bytes, bool]:
        chunked_data = bytearray()
        while True:
            # print(' '.join(format(x, '02x') for x in response_body))

            length_crlf_idx = response_body.find(b"\r\n")
            if length_crlf_idx == -1:
                break

            hex_length = response_body[:length_crlf_idx]
            try:
                length = int(hex_length, 16)
            except ValueError as e:
                logging.error(f"Parsing chunked length failed: {e}")
                break

            if length == 0:
                length_crlf_idx = response_body.find(b"0\r\n\r\n")
                if length_crlf_idx != -1:
                    return chunked_data, True

            if length + 2 > len(response_body):
                break

            chunked_data.extend(response_body[length_crlf_idx + 2:length_crlf_idx + 2 + length])
            if length_crlf_idx + 2 + length + 2 > len(response_body):
                break

            response_body = response_body[length_crlf_idx + 2 + length + 2:]
        return chunked_data, False
