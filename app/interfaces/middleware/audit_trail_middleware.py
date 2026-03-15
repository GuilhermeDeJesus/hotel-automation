"""Middleware de Audit Trail para logging automático de ações."""
import json
import time
import uuid
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.infrastructure.persistence.sql.audit_trail_repository import AuditTrailService
from app.interfaces.dependencies.auth import get_current_user_from_token
from app.infrastructure.persistence.sql.models import UserModel


class AuditTrailMiddleware(BaseHTTPMiddleware):
    """Middleware que automaticamente registra todas as ações no audit trail."""
    
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or {
            "/health", "/docs", "/openapi.json", "/favicon.ico", "/static"
        }
        self.excluded_actions = {"GET"}  # Ações excluídas do logging automático
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Pular logging para paths excluídos
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Extrair informações do request
        request_info = self._extract_request_info(request)
        
        # Tentar obter usuário
        user = None
        try:
            user = self._get_user_from_request(request)
        except Exception:
            pass  # Usuário não autenticado
        
        # Executar a request
        response = await call_next(request)
        
        # Calcular tempo de execução
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Determinar se deve fazer logging
        if self._should_log_action(request, response, user):
            await self._log_action(request, response, user, request_info, execution_time_ms)
        
        return response
    
    def _extract_request_info(self, request: Request) -> Dict[str, Any]:
        """Extrai informações relevantes do request."""
        return {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "ip_address": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length")
        }
    
    def _get_user_from_request(self, request: Request) -> Optional[UserModel]:
        """Tenta extrair usuário do request."""
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            return get_current_user_from_token(token)
        return None
    
    def _get_client_ip(self, request: Request) -> str:
        """Extrai IP real do cliente."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else "unknown"
    
    def _should_log_action(self, request: Request, response: Response, user: Optional[UserModel]) -> bool:
        """Determina se a ação deve ser logada."""
        # Não logar requests GET (leitura)
        if request.method in self.excluded_actions:
            return False
        
        # Logar requests que modificam dados
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            return True
        
        # Logar endpoints de autenticação
        if "/auth" in request.url.path or "/login" in request.url.path:
            return True
        
        # Logar endpoints admin
        if "/admin" in request.url.path:
            return True
        
        # Logar se houver erro
        if response.status_code >= 400:
            return True
        
        return False
    
    async def _log_action(
        self,
        request: Request,
        response: Response,
        user: Optional[UserModel],
        request_info: Dict[str, Any],
        execution_time_ms: int
    ):
        """Registra a ação no audit trail."""
        try:
            # Determinar hotel_id
            hotel_id = self._get_hotel_id(user, request)
            if not hotel_id:
                return  # Não logar se não tiver hotel_id
            
            # Criar serviço de audit trail
            from app.infrastructure.persistence.sql.database import SessionLocal
            session = SessionLocal()
            audit_service = AuditTrailService(session)
            
            # Determinar tipo de ação e recurso
            action, resource_type, resource_id = self._classify_action(request, response)
            
            # Criar descrição
            description = self._create_description(request, response)
            
            # Extrair detalhes (se houver body)
            details = await self._extract_details(request, response)
            
            # Determinar status
            status = self._determine_status(response)
            
            # Logar erro se houver
            error_message = None
            if response.status_code >= 400:
                try:
                    error_details = await self._extract_error_details(response)
                    error_message = error_details.get("detail", "Unknown error")
                except:
                    error_message = f"HTTP {response.status_code}"
            
            # Registrar no audit trail
            audit_service.log_action(
                hotel_id=hotel_id,
                user_id=user.id if user else "anonymous",
                user_email=user.email if user else "anonymous",
                user_role=user.role if user else "anonymous",
                action=action,
                resource_type=resource_type,
                description=description,
                resource_id=resource_id,
                details=details,
                ip_address=request_info["ip_address"],
                user_agent=request_info["user_agent"],
                endpoint=request_info["path"],
                method=request_info["method"],
                request_id=str(uuid.uuid4()),
                status=status,
                error_message=error_message,
                execution_time_ms=execution_time_ms
            )
            
            session.commit()
            
        except Exception as e:
            # Não falhar a request por erro no audit trail
            print(f"Erro ao registrar audit trail: {str(e)}")
            try:
                session.rollback()
            except:
                pass
    
    def _get_hotel_id(self, user: Optional[UserModel], request: Request) -> Optional[str]:
        """Determina o hotel_id para logging."""
        if user and user.hotel_id:
            return user.hotel_id
        
        # Para endpoints de criação de usuário, tentar extrair do body
        if "/auth/register" in request.url.path:
            # Implementar lógica para extrair hotel_id do request body
            pass
        
        return None
    
    def _classify_action(self, request: Request, response: Response) -> tuple:
        """Classifica a ação em tipo, resource_type e resource_id."""
        method = request.method
        path = request.url.path
        
        # Autenticação
        if "/auth/login" in path:
            return "LOGIN", "auth", None
        elif "/auth/logout" in path:
            return "LOGOUT", "auth", None
        elif "/auth/register" in path:
            return "CREATE", "user", None
        
        # Reservas
        elif "/reservations" in path:
            if method == "POST":
                return "CREATE", "reservation", None
            elif method == "PUT":
                return "UPDATE", "reservation", self._extract_id_from_path(path)
            elif method == "DELETE":
                return "DELETE", "reservation", self._extract_id_from_path(path)
        
        # Quartos
        elif "/rooms" in path:
            if method == "POST":
                return "CREATE", "room", None
            elif method == "PUT":
                return "UPDATE", "room", self._extract_id_from_path(path)
            elif method == "DELETE":
                return "DELETE", "room", self._extract_id_from_path(path)
        
        # Usuários
        elif "/users" in path:
            if method == "POST":
                return "CREATE", "user", None
            elif method == "PUT":
                return "UPDATE", "user", self._extract_id_from_path(path)
            elif method == "DELETE":
                return "DELETE", "user", self._extract_id_from_path(path)
        
        # Admin
        elif "/admin" in path:
            return "ADMIN", "admin", None
        
        # WhatsApp
        elif "/whatsapp" in path:
            return "WHATSAPPOT", "whatsapp", None
        
        # Padrão
        else:
            return method, "unknown", None
    
    def _extract_id_from_path(self, path: str) -> Optional[str]:
        """Extrai ID do path da URL."""
        parts = path.strip("/").split("/")
        for part in parts:
            if len(part) == 36 or part.replace("-", "").isalnum():  # UUID-like
                return part
        return None
    
    def _create_description(self, request: Request, response: Response) -> str:
        """Cria descrição legível da ação."""
        method = request.method
        path = request.url.path
        
        if method == "POST":
            return f"Criou recurso em {path}"
        elif method == "PUT":
            return f"Atualizou recurso em {path}"
        elif method == "DELETE":
            return f"Removeu recurso em {path}"
        elif method == "PATCH":
            return f"Modificou recurso em {path}"
        else:
            return f"Executou {method} em {path}"
    
    async def _extract_details(self, request: Request, response: Response) -> Optional[Dict]:
        """Extrai detalhes do request/response."""
        details = {
            "request_method": request.method,
            "request_path": request.url.path,
            "response_status": response.status_code
        }
        
        # Adicionar query params se houver
        if request.query_params:
            details["query_params"] = dict(request.query_params)
        
        return details
    
    def _determine_status(self, response: Response) -> str:
        """Determina o status da ação baseado no response."""
        if response.status_code < 400:
            return "SUCCESS"
        elif 400 <= response.status_code < 500:
            return "FAILED"
        else:
            return "ERROR"
    
    async def _extract_error_details(self, response: Response) -> Dict:
        """Extrai detalhes de erro do response."""
        try:
            if hasattr(response, 'body'):
                body = response.body
                if isinstance(body, bytes):
                    body = body.decode('utf-8')
                return json.loads(body)
        except:
            pass
        return {"detail": f"HTTP {response.status_code}"}


# Função de conveniência para logging manual
def log_audit_action(
    hotel_id: str,
    user: UserModel,
    action: str,
    resource_type: str,
    description: str,
    resource_id: str = None,
    details: Dict = None,
    status: str = "SUCCESS",
    error_message: str = None
):
    """
    Função de conveniência para logging manual de ações.
    
    Uso:
        log_audit_action(
            hotel_id=user.hotel_id,
            user=user,
            action="CREATE",
            resource_type="reservation",
            description="Criou nova reserva",
            resource_id=reservation.id,
            details={"guest_name": reservation.guest_name}
        )
    """
    from app.infrastructure.persistence.sql.database import SessionLocal
    
    session = SessionLocal()
    try:
        audit_service = AuditTrailService(session)
        audit_service.log_action(
            hotel_id=hotel_id,
            user_id=user.id,
            user_email=user.email,
            user_role=user.role,
            action=action,
            resource_type=resource_type,
            description=description,
            resource_id=resource_id,
            details=details,
            status=status,
            error_message=error_message
        )
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
