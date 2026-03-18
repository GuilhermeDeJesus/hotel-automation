import os
import requests
import json
import logging
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class WhatsAppMetaClient:
    """Cliente para Meta WhatsApp Cloud API v18.0
    
    Documentação: https://developers.facebook.com/docs/whatsapp/cloud-api/
    """
    
    def __init__(self):
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("PHONE_NUMBER_ID")
        
        if not self.access_token or not self.phone_number_id:
            raise ValueError(
                "META_ACCESS_TOKEN e PHONE_NUMBER_ID são obrigatórios no .env"
            )
        
        self.api_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def send_text_message(self, to_phone: str, message: str) -> Dict[str, Any]:
        """
        Envia mensagem de texto via WhatsApp.
        
        Args:
            to_phone: Número do destinatário (ex: "5561998776092")
            message: Conteúdo da mensagem
        
        Returns:
            Dict com sucesso/erro
        
        Exemplo:
            result = client.send_text_message("5561998776092", "Olá!")
            if result["success"]:
                print(f"Mensagem enviada: {result['message_id']}")
        """
        
        # Formata número
        to_phone = self._format_phone(to_phone)
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/messages",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id")
                logger.info(f"✅ Mensagem enviada para {to_phone}: {message_id}")
                return {
                    "success": True,
                    "message_id": message_id,
                    "data": data
                }
            else:
                error_msg = response.text
                logger.error(f"❌ Erro ao enviar para {to_phone}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": response.status_code
                }
        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout ao enviar para {to_phone}")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            logger.error(f"❌ Erro desconhecido: {str(e)}")
            return {"success": False, "error": str(e)}

    def send_image_message(
        self,
        to_phone: str,
        message: str,
        media_url: str,
    ) -> Dict[str, Any]:
        """
        Envia mensagem de imagem via WhatsApp (Meta Cloud API).

        Observação: 'message' vai como caption.
        """
        to_phone = self._format_phone(to_phone)

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "image",
            "image": {"link": media_url},
            "caption": message or "",
        }

        try:
            response = requests.post(
                f"{self.api_url}/messages",
                json=payload,
                headers=self.headers,
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id")
                logger.info(f"✅ Mensagem com imagem enviada para {to_phone}: {message_id}")
                return {"success": True, "message_id": message_id, "data": data}
            else:
                error_msg = response.text
                logger.error(f"❌ Erro ao enviar imagem para {to_phone}: {error_msg}")
                return {"success": False, "error": error_msg, "status_code": response.status_code}
        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout ao enviar imagem para {to_phone}")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            logger.error(f"❌ Erro desconhecido ao enviar imagem: {str(e)}")
            return {"success": False, "error": str(e)}

    def send_template_message(
        self,
        to_phone: str,
        template_name: str = "hello_world",
        language_code: str = "en_US",
        components: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Envia mensagem template (necessario fora da janela de 24h).
        
        Args:
            to_phone: Numero do destinatario
            template_name: Nome do template aprovado (padrao: hello_world)
            language_code: Codigo de idioma (padrao: en_US)
            components: Componentes opcionais do template
        """
        
        to_phone = self._format_phone(to_phone)
        
        template_payload: Dict[str, Any] = {
            "name": template_name,
            "language": {"code": language_code}
        }
        
        if components:
            template_payload["components"] = components
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "template",
            "template": template_payload
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/messages",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id")
                logger.info(f"✅ Template enviado para {to_phone}: {message_id}")
                return {"success": True, "message_id": message_id, "data": data}
            else:
                error_msg = response.text
                logger.error(f"❌ Erro ao enviar template para {to_phone}: {error_msg}")
                return {"success": False, "error": error_msg, "status_code": response.status_code}
        except Exception as e:
            logger.error(f"❌ Erro ao enviar template: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_button_message(
        self, 
        to_phone: str, 
        message: str, 
        buttons: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Envia mensagem com botões interativos.
        
        Args:
            to_phone: Número do destinatário
            message: Texto da mensagem
            buttons: Lista de botões (máx 3)
                Ex: [
                    {"id": "1", "title": "Reservar"},
                    {"id": "2", "title": "Ver Estadia"}
                ]
        
        Returns:
            Dict com sucesso/erro
        """
        
        to_phone = self._format_phone(to_phone)
        
        # Limita a 3 botões (limite Meta)
        buttons = buttons[:3]
        
        button_list = [
            {
                "type": "reply",
                "reply": {
                    "id": btn["id"],
                    "title": btn["title"]
                }
            }
            for btn in buttons
        ]
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": message
                },
                "action": {
                    "buttons": button_list
                }
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/messages",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id")
                logger.info(f"✅ Mensagem com botões enviada para {to_phone}: {message_id}")
                return {"success": True, "message_id": message_id, "data": data}
            else:
                error_msg = response.text
                logger.error(f"❌ Erro ao enviar botões para {to_phone}: {error_msg}")
                return {"success": False, "error": error_msg, "status_code": response.status_code}
        except Exception as e:
            logger.error(f"❌ Erro ao enviar botões: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_list_message(
        self,
        to_phone: str,
        header: str,
        body: str,
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Envia mensagem com lista (menu).
        
        Args:
            to_phone: Número do destinatário
            header: Título da lista
            body: Descrição
            items: Lista de items
                Ex: [
                    {
                        "id": "1",
                        "title": "Check-in",
                        "description": "Fazer check-in agora"
                    }
                ]
        """
        
        to_phone = self._format_phone(to_phone)
        
        formatted_items = [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "description": item.get("description", "")
            }
            for item in items[:10]  # Máx 10 items
        ]
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {
                    "type": "text",
                    "text": header
                },
                "body": {
                    "text": body
                },
                "action": {
                    "button": "Ver opções",
                    "sections": [
                        {
                            "title": header,
                            "rows": formatted_items
                        }
                    ]
                }
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/messages",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id")
                logger.info(f"✅ Mensagem com lista enviada para {to_phone}: {message_id}")
                return {"success": True, "message_id": message_id, "data": data}
            else:
                error_msg = response.text
                logger.error(f"❌ Erro ao enviar lista para {to_phone}: {error_msg}")
                return {"success": False, "error": error_msg, "status_code": response.status_code}
        except Exception as e:
            logger.error(f"❌ Erro ao enviar lista: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Marca mensagem como lida (double blue check).
        
        Args:
            message_id: ID da mensagem recebida
        
        Returns:
            Dict com sucesso/erro
        """
        
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/messages",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Mensagem {message_id} marcada como lida")
                return {"success": True}
            else:
                logger.error(f"❌ Erro ao marcar como lida: {response.text}")
                return {"success": False, "error": response.text}
        except Exception as e:
            logger.error(f"❌ Erro ao marcar como lida: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_contacts(self) -> Dict[str, Any]:
        """
        Retorna lista de contatos de teste (sandbox).
        
        Returns:
            Lista de contatos
        """
        
        try:
            response = requests.get(
                f"{self.api_url}/contacts",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _format_phone(phone: str) -> str:
        """
        Formata número para padrão WhatsApp.
        
        Regras:
        - Remove caracteres especiais
        - Adiciona código país se não tiver
        - Formato final: 5561998776092 (sem + ni traços)
        
        Args:
            phone: Número em qualquer formato
        
        Returns:
            Número formatado
        """
        
        # Remove tudo que não é dígito
        phone = "".join(filter(str.isdigit, phone))
        
        # Se não começa com 55 (código Brasil), adiciona
        if not phone.startswith("55"):
            phone = "55" + phone
        
        return phone
    
    def test_connection(self) -> bool:
        """
        Testa se a conexão com Meta API está funcionando.
        
        Returns:
            True se OK, False se erro
        """
        
        try:
            response = requests.get(
                f"{self.api_url}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ Conexão com Meta API OK!")
                return True
            else:
                logger.error(f"❌ Erro na conexão: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Erro na conexão: {str(e)}")
            return False
