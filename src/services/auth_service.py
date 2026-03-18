import json
from dataclasses import dataclass
from typing import Optional, Any

import httpx
import jsonpath_ng

from models.auth_config import AuthConfig
from utils.logger import get_logger

_logger = get_logger("services.auth_service")


@dataclass
class AuthResult:
    success: bool
    token: Optional[str] = None
    header_name: str = "Authorization"
    header_value: Optional[str] = None
    raw_response: Optional[dict] = None
    error_message: Optional[str] = None
    status_code: Optional[int] = None


class AuthService:
    @staticmethod
    def execute_login(auth_config: AuthConfig, timeout: float = 30.0) -> AuthResult:
        try:
            url = f"{auth_config.base_url.rstrip('/')}{auth_config.login_path}"
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            if auth_config.headers:
                headers.update(auth_config.headers)
            
            _logger.info(f"执行登录请求: {auth_config.method} {url}")
            
            with httpx.Client(timeout=timeout) as client:
                if auth_config.method.upper() == "GET":
                    response = client.get(url, headers=headers, params=auth_config.body)
                else:
                    response = client.request(
                        method=auth_config.method.upper(),
                        url=url,
                        headers=headers,
                        json=auth_config.body if auth_config.body else None
                    )
            
            _logger.info(f"登录响应状态码: {response.status_code}")
            
            if response.status_code >= 400:
                return AuthResult(
                    success=False,
                    error_message=f"登录失败，HTTP 状态码: {response.status_code}",
                    status_code=response.status_code
                )
            
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                return AuthResult(
                    success=False,
                    error_message="响应不是有效的 JSON 格式",
                    status_code=response.status_code
                )
            
            token = AuthService._extract_token(response_data, auth_config.token_path)
            
            if not token:
                return AuthResult(
                    success=False,
                    error_message=f"无法从响应中提取 Token，路径: {auth_config.token_path}",
                    raw_response=response_data,
                    status_code=response.status_code
                )
            
            header_value = AuthService._build_header_value(
                token, 
                auth_config.token_prefix, 
                auth_config.header_name
            )
            
            _logger.info(f"登录成功，Token 已提取")
            
            return AuthResult(
                success=True,
                token=token,
                header_name=auth_config.header_name,
                header_value=header_value,
                raw_response=response_data,
                status_code=response.status_code
            )
            
        except httpx.TimeoutException:
            error_msg = f"请求超时 ({timeout}秒)"
            _logger.error(error_msg)
            return AuthResult(success=False, error_message=error_msg)
        except httpx.ConnectError as e:
            error_msg = f"连接失败: {str(e)}"
            _logger.error(error_msg)
            return AuthResult(success=False, error_message=error_msg)
        except Exception as e:
            error_msg = f"登录请求异常: {str(e)}"
            _logger.error(error_msg)
            return AuthResult(success=False, error_message=error_msg)
    
    @staticmethod
    def _extract_token(response_data: dict, token_path: str) -> Optional[str]:
        if not token_path:
            return None
        
        if token_path.startswith("$."):
            try:
                jsonpath_expr = jsonpath_ng.parse(token_path)
                matches = jsonpath_expr.find(response_data)
                if matches:
                    token = matches[0].value
                    if isinstance(token, str):
                        return token
                    return str(token)
            except Exception as e:
                _logger.error(f"JSONPath 解析失败: {e}")
        
        keys = token_path.replace("$.", "").split(".")
        current = response_data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        if isinstance(current, str):
            return current
        return str(current) if current else None
    
    @staticmethod
    def _build_header_value(token: str, token_prefix: str, header_name: str) -> str:
        if header_name.lower() == "authorization":
            if token_prefix:
                return f"{token_prefix} {token}"
            return token
        return token
    
    @staticmethod
    def get_auth_header_for_request(auth_config: AuthConfig) -> Optional[dict]:
        result = AuthService.execute_login(auth_config)
        if result.success and result.header_value:
            return {result.header_name: result.header_value}
        return None
