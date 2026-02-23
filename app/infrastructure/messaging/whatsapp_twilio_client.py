import os
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

load_dotenv()

logger = logging.getLogger(__name__)


class WhatsAppTwilioClient:
    """Cliente para Twilio WhatsApp API
    
    Documentação: https://www.twilio.com/docs/whatsapp/api
    """
    
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
        
        if not all([self.account_sid, self.auth_token, self.from_number]):
            raise ValueError(
                "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN e TWILIO_WHATSAPP_NUMBER "
                "são obrigatórios no .env"
            )
        
        # Inicializa cliente Twilio
        self.client = Client(self.account_sid, self.auth_token)
        
        # Formata número "from" com prefixo whatsapp:
        if not self.from_number.startswith("whatsapp:"):
            self.from_number = f"whatsapp:{self.from_number}"
        
        logger.info(f"✅ Twilio WhatsApp Client inicializado: {self.from_number}")
    
    def send_text_message(self, to_phone: str, message: str) -> Dict[str, Any]:
        """
        Envia mensagem de texto via WhatsApp.
        
        Args:
            to_phone: Número do destinatário (ex: "+5561998776092")
            message: Conteúdo da mensagem
        
        Returns:
            Dict com sucesso/erro
        
        Exemplo:
            result = client.send_text_message("+5561998776092", "Olá!")
            if result["success"]:
                print(f"Mensagem enviada: {result['sid']}")
        """
        
        # Formata número
        to_phone = self._format_phone(to_phone)
        
        try:
            message_obj = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_phone
            )
            
            logger.info(f"✅ Mensagem enviada para {to_phone}: {message_obj.sid}")
            
            return {
                "success": True,
                "sid": message_obj.sid,
                "status": message_obj.status,
                "to": to_phone,
                "from": self.from_number
            }
        
        except TwilioRestException as e:
            logger.error(f"❌ Erro Twilio ao enviar para {to_phone}: {e.msg}")
            return {
                "success": False,
                "error": e.msg,
                "code": e.code,
                "status": e.status
            }
        except Exception as e:
            logger.error(f"❌ Erro desconhecido: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_media_message(
        self, 
        to_phone: str, 
        message: str, 
        media_url: str
    ) -> Dict[str, Any]:
        """
        Envia mensagem com mídia (imagem, PDF, etc).
        
        Args:
            to_phone: Número do destinatário
            message: Texto da mensagem
            media_url: URL pública da mídia
        
        Returns:
            Dict com sucesso/erro
        """
        
        to_phone = self._format_phone(to_phone)
        
        try:
            message_obj = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_phone,
                media_url=[media_url]
            )
            
            logger.info(f"✅ Mensagem com mídia enviada para {to_phone}: {message_obj.sid}")
            
            return {
                "success": True,
                "sid": message_obj.sid,
                "status": message_obj.status
            }
        
        except TwilioRestException as e:
            logger.error(f"❌ Erro ao enviar mídia para {to_phone}: {e.msg}")
            return {"success": False, "error": e.msg, "code": e.code}
        except Exception as e:
            logger.error(f"❌ Erro ao enviar mídia: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_template_message(
        self,
        to_phone: str,
        content_sid: str,
        content_variables: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Envia mensagem template aprovada (Twilio Content API).
        
        Args:
            to_phone: Número do destinatário
            content_sid: SID do template aprovado
            content_variables: Variáveis do template
        
        Returns:
            Dict com sucesso/erro
        """
        
        to_phone = self._format_phone(to_phone)
        
        try:
            params = {
                "from_": self.from_number,
                "to": to_phone,
                "content_sid": content_sid
            }
            
            if content_variables:
                params["content_variables"] = str(content_variables)
            
            message_obj = self.client.messages.create(**params)
            
            logger.info(f"✅ Template enviado para {to_phone}: {message_obj.sid}")
            
            return {
                "success": True,
                "sid": message_obj.sid,
                "status": message_obj.status
            }
        
        except TwilioRestException as e:
            logger.error(f"❌ Erro ao enviar template: {e.msg}")
            return {"success": False, "error": e.msg, "code": e.code}
        except Exception as e:
            logger.error(f"❌ Erro ao enviar template: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """
        Consulta status de uma mensagem enviada.
        
        Args:
            message_sid: SID da mensagem
        
        Returns:
            Dict com status
        """
        
        try:
            message = self.client.messages(message_sid).fetch()
            
            return {
                "success": True,
                "sid": message.sid,
                "status": message.status,
                "to": message.to,
                "from": message.from_,
                "date_sent": str(message.date_sent),
                "error_code": message.error_code,
                "error_message": message.error_message
            }
        
        except TwilioRestException as e:
            logger.error(f"❌ Erro ao buscar status: {e.msg}")
            return {"success": False, "error": e.msg}
        except Exception as e:
            logger.error(f"❌ Erro ao buscar status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _format_phone(phone: str) -> str:
        """
        Formata número para padrão Twilio WhatsApp.
        
        Twilio usa formato: whatsapp:+5561998776092
        
        Args:
            phone: Número em qualquer formato
        
        Returns:
            Número formatado com prefixo whatsapp:
        """
        
        # Remove espaços e caracteres especiais
        phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        # Se já tem whatsapp:, retorna
        if phone.startswith("whatsapp:"):
            return phone
        
        # Se não tem +, adiciona
        if not phone.startswith("+"):
            # Se é BR e não tem código país, adiciona 55
            if not phone.startswith("55"):
                phone = "55" + phone
            phone = "+" + phone
        
        # Adiciona prefixo whatsapp:
        return f"whatsapp:{phone}"
    
    def test_connection(self) -> bool:
        """
        Testa se as credenciais Twilio estão válidas.
        
        Returns:
            True se OK, False se erro
        """
        
        try:
            # Tenta buscar info da conta
            account = self.client.api.accounts(self.account_sid).fetch()
            logger.info(f"✅ Conexão Twilio OK! Account: {account.friendly_name}")
            return True
        except TwilioRestException as e:
            logger.error(f"❌ Erro na conexão Twilio: {e.msg}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro na conexão: {str(e)}")
            return False
