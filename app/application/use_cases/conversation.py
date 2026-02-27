"""
Conversation Use-Case - orchestrates AI-powered multi-turn conversations.

Coordinates between:
- AIService: Language model for generating responses
- ReservationRepository: Access to guest/reservation data
- CacheRepository: Persistent conversation history
- MessagingProvider: Send responses back to guest
"""
from typing import Optional, List

from app.domain.value_objects.message import Message
from app.domain.repositories.cache_repository import CacheRepository
from app.domain.repositories.reservation_repository import ReservationRepository
from app.application.services.ai_service import AIService
from app.application.services.interaction_logger import InteractionLogger
from app.application.services.reservation_context_service import ReservationContextService
from app.application.services.hotel_context_service import HotelContextService
from app.application.exceptions import ConversationFailed, CacheError, AIServiceError


class ConversationUseCase:
    """
    Orchestrates multi-turn conversations with AI and history caching.
    
    Maintains conversation history in cache for multi-turn context,
    allowing the AI to reference previous messages in the conversation.
    """

    def __init__(
        self,
        ai_service: AIService,
        reservation_repo: ReservationRepository,
        cache_repository: CacheRepository,
        context_service: ReservationContextService,
        hotel_context_service: HotelContextService,
        messaging: Optional[object] = None,
        logger: Optional[InteractionLogger] = None,
    ):
        """
        Initialize conversation orchestrator.
        
        Args:
            ai_service: AIService implementation (e.g., OpenAIClient)
            reservation_repo: Repository for accessing reservations
            cache_repository: CacheRepository for conversation history
            context_service: ReservationContextService for fetching guest context
            hotel_context_service: HotelContextService for hotel information
            messaging: Optional messaging provider for sending responses
            logger: Optional ConversationLogger for recording interactions
        """
        self.ai = ai_service
        self.reservation_repo = reservation_repo
        self.cache_repository = cache_repository
        self.context_service = context_service
        self.hotel_context_service = hotel_context_service
        self.messaging = messaging
        self.logger = logger

    def execute(self, phone: str, text: str) -> str:
        """
        Execute a single conversation turn.

        Retrieves previous messages from cache, adds user message,
        calls AI for response, updates cache, and optionally sends message.
        
        Args:
            phone: Guest phone number
            text: User message text
            
        Returns:
            AI response text
            
        Raises:
            ConversationFailed: If conversation orchestration fails
            CacheError: If cache operation fails
            AIServiceError: If AI service call fails
        """
        try:
            # Get conversation history from cache
            history_dicts = self._get_conversation_history(phone)
            
            # Convert dicts to Message value objects
            messages: List[Message] = [
                Message(role=msg["role"], content=msg["content"])
                for msg in history_dicts
            ]
            
            # Create and add user message
            user_message = Message(role="user", content=text)
            messages.append(user_message)
            
            # Call AI with conversation history and reservation context
            ai_response = self._call_ai(messages, phone)
            
            # Create and add assistant message
            assistant_message = Message(role="assistant", content=ai_response)
            messages.append(assistant_message)
            
            # Update cache with full conversation
            self._update_conversation_history(phone, messages)
            
            # Log interaction to persistent storage
            self._log_interaction(phone, text, ai_response)
            
            # Send response if messaging provider available
            if self.messaging:
                self._send_message(phone, ai_response)
            
            return ai_response
            
        except (CacheError, AIServiceError) as e:
            raise ConversationFailed(f"Conversation failed: {str(e)}")
        except Exception as e:
            raise ConversationFailed(f"Unexpected error in conversation: {str(e)}")

    def _get_conversation_history(self, phone: str) -> list:
        """
        Retrieve conversation history from cache.
        
        Args:
            phone: Guest phone number
            
        Returns:
            List of message dicts with 'role' and 'content'
        """
        try:
            history = self.cache_repository.get(phone)
            return history if history else []
        except Exception as e:
            raise CacheError(f"Failed to retrieve conversation history: {str(e)}")

    def _call_ai(self, messages: List[Message], phone: str = None) -> str:
        """
        Call AI service with message history and hotel/reservation context.
        
        Args:
            messages: List of Message value objects
            phone: Optional guest phone number for context retrieval
            
        Returns:
            AI response text
        """
        try:
            # Convert Messages back to dicts for AI service
            message_dicts = [msg.to_dict() for msg in messages]
            
            # Prepend hotel and reservation context if available
            system_message = "Você é um assistente de hotel prestativo e profissional. Responde às mensagens dos hóspedes de forma clara e amigável. Sempre que possível, utilize as informações da reserva e do hotel para fornecer respostas personalizadas e úteis. Não pergunte por número de noites, sempre peça por datas de checkin e checkout. Responsa de forma mais humanizada possível, não seja um robô, seja um atendente humano. Se o hóspede fornecer datas de checkin e checkout, responda com a disponibilidade e preços para esse período, e ofereça opções de quartos. Se o hóspede perguntar sobre serviços do hotel, forneça informações detalhadas sobre os serviços disponíveis, como café da manhã, piscina, academia, etc. Se o hóspede tiver uma reserva existente, utilize as informações da reserva para responder às perguntas de forma personalizada."
            hotel_context = self.hotel_context_service.get_context()
            if hotel_context:
                system_message += f"\n\n{hotel_context}"
            if phone:
                reservation_context = self.context_service.get_context_for_phone(phone)
                if reservation_context:
                    system_message += f"\n\n{reservation_context}"
            
            # Inject system message with context at the beginning
            message_dicts.insert(0, {"role": "system", "content": system_message})
            
            ai_response = self.ai.chat(message_dicts)
            
            # Handle different response formats
            if isinstance(ai_response, dict):
                # Handle both new and old OpenAI SDK formats
                if "content" in ai_response:
                    return ai_response["content"]
                elif "choices" in ai_response:
                    return ai_response["choices"][0]["message"]["content"]
                else:
                    raise AIServiceError("Unexpected AI response format")
            else:
                return str(ai_response)
                
        except Exception as e:
            raise AIServiceError(f"AI service call failed: {str(e)}")

    def _update_conversation_history(self, phone: str, messages: List[Message]) -> None:
        """
        Update conversation history in cache.
        
        Args:
            phone: Guest phone number
            messages: List of Message value objects
        """
        try:
            # Convert Messages to dicts for storage
            message_dicts = [msg.to_dict() for msg in messages]
            self.cache_repository.set(phone, message_dicts, ttl_seconds=3600)
        except Exception as e:
            raise CacheError(f"Failed to update conversation history: {str(e)}")

    def _send_message(self, phone: str, message: str) -> None:
        """
        Send message via messaging provider.
        
        Args:
            phone: Recipient phone number
            message: Message text to send
        """
        try:
            if self.messaging:
                self.messaging.send(phone, message)
        except Exception as e:
            # Log but don't fail - message was generated successfully
            # Messaging failure shouldn't break the conversation
            raise ConversationFailed(f"Failed to send message: {str(e)}")

    def _log_interaction(self, phone: str, user_message: str, ai_response: str) -> None:
        """
        Log interaction to persistent storage.
        Estimating tokens using character count / 4 (rough OpenAI approximation).
        
        Args:
            phone: Guest phone number
            user_message: User message text
            ai_response: AI response text
        """
        try:
            if not self.logger:
                return

            # Rough token estimation: OpenAI uses ~4 chars per token average
            tokens_input = len(user_message) // 4 or 1
            tokens_output = len(ai_response) // 4 or 1
            
            self.logger.log_interaction(
                phone=phone,
                user_message=user_message,
                ai_response=ai_response,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                model="gpt-3.5-turbo",
                metadata={"source": "conversation_use_case"}
            )
        except Exception:
            # Log failures don't break the conversation flow
            # They are informational only
            pass