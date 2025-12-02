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
                self.logger.debug("响应完成，重置缓冲状态")

            return result
        except Exception as e:
            raise e

    def parse_response(self, response_data):
        # 添加诊断日志
        if response_data:
            self.logger.debug(f"parse_response: 接收到 {len(response_data)} 字节数据")
            self.logger.debug(f"parse_response: 数据前 200 字节: {response_data[:200]}")

        pattern = rb'\[\[\[null,.*?],"model"]]'
        matches = []
        for match_obj in re.finditer(pattern, response_data):
            matches.append(match_obj.group(0))

        self.logger.debug(f"parse_response: 正则匹配到 {len(matches)} 个 JSON 块")


        resp = {
            "reason": "",
            "body": "",
            "function": [],
        }

        # Print each full match
        for match in matches:
            try:
                json_data = json.loads(match)
            except json.JSONDecodeError as je:
                # JSON 解析失败，跳过这个块
                self.logger.debug(f"跳过无效的 JSON 块 (位置 {je.pos}): {match[:100]}...")
                continue
            except Exception as e:
                # 其他解析错误
                self.logger.debug(f"JSON 解析遇到异常: {e}, 跳过该块")
                continue

            try:
                payload = json_data[0][0]
            except Exception as e:
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
                        tool_payload = json.loads(json_str)
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
                # 注意：不立即清空缓冲区，以支持跨 chunk 检测
                # 但如果缓冲区没有可能的标记起始符（反引号），则可以安全发送
                if '`' not in self._tool_call_buffer:
                    # 完全安全，立即发送所有内容
                    resp["body"] = self._tool_call_buffer
                    self._tool_call_buffer = ""
                else:
                    # 可能包含分散的标记，保留最后一小段用于跨 chunk 检测
                    # 保留最后 10 个字符（足够包含 "```json" 的任何前缀）
                    MAX_WINDOW = 10
                    if len(self._tool_call_buffer) > MAX_WINDOW:
                        safe_to_send = self._tool_call_buffer[:-MAX_WINDOW]
                        resp["body"] = safe_to_send
                        self._tool_call_buffer = self._tool_call_buffer[-MAX_WINDOW:]
                    else:
                        # 缓冲区不够长，暂时不发送
                        resp["body"] = ""
        # ---------------------------------------------------------

        return resp

    def _reset_buffer_state(self):
        """重置缓冲状态（在响应结束时调用）"""
        self._tool_call_buffer = ""
        self._is_buffering = False
        self._buffer_start_time = None
        self._keepalive_count = 0

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
