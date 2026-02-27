"""
Conversation Logger - Registra histórico de todas as interações com OpenAI.

Mantém um log permanente em JSON com:
- Timestamp
- Phone/User ID
- Mensagem do usuário
- Resposta do AI
- Tokens gastos
- Custo estimado
"""
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from app.application.services.interaction_logger import InteractionLogger


class ConversationLogger(InteractionLogger):
    """
    Mantém registro persistente de todas as conversas em JSON.
    
    Ideal para:
    - Auditar conversas
    - Rastrear custos
    - Análise de padrões
    - Conformidade/compliance
    """
    
    def __init__(self, log_dir: str = "logs", log_file: str = "conversation_history.json"):
        """
        Initialize logger.
        
        Args:
            log_dir: Diretório para armazenar logs
            log_file: Nome do arquivo JSON
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.log_file = self.log_dir / log_file
        self.conversations = self._load_or_create()
    
    def _load_or_create(self) -> list:
        """Load existing log or create new."""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []
    
    def log_interaction(
        self,
        phone: str,
        user_message: str,
        ai_response: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        model: str = "gpt-3.5-turbo",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a single user-AI interaction.
        
        Args:
            phone: User phone number
            user_message: What user said
            ai_response: What AI responded
            tokens_input: Input tokens used
            tokens_output: Output tokens used
            model: Model used (e.g., gpt-3.5-turbo)
            metadata: Optional additional data
        """
        # Calculate costs (prices as of Feb 2026)
        cost_input = (tokens_input / 1_000_000) * 0.50  # $0.50 per 1M for 3.5-turbo
        cost_output = (tokens_output / 1_000_000) * 1.50  # $1.50 per 1M for 3.5-turbo
        total_cost = cost_input + cost_output
        
        entry = {
            "id": len(self.conversations) + 1,
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "phone": phone,
            "user_message": user_message[:500],  # Limita 500 chars
            "ai_response": ai_response[:500],
            "model": model,
            "tokens": {
                "input": tokens_input,
                "output": tokens_output,
                "total": tokens_input + tokens_output
            },
            "cost": {
                "input_usd": round(cost_input, 6),
                "output_usd": round(cost_output, 6),
                "total_usd": round(total_cost, 6)
            },
            "metadata": metadata or {}
        }
        
        self.conversations.append(entry)
        self._save()
    
    def _save(self) -> None:
        """Save conversations to JSON file."""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversations, f, indent=2, ensure_ascii=False)
        except IOError as e:
            raise IOError(f"Failed to save log: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics.
        
        Returns:
            Dictionary with stats
        """
        if not self.conversations:
            return {
                "total_interactions": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "avg_tokens_per_interaction": 0,
                "avg_cost_per_interaction": 0.0
            }
        
        total = len(self.conversations)
        total_tokens = sum(c["tokens"]["total"] for c in self.conversations)
        total_cost = sum(c["cost"]["total_usd"] for c in self.conversations)
        
        return {
            "total_interactions": total,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "avg_tokens_per_interaction": round(total_tokens / total),
            "avg_cost_per_interaction": round(total_cost / total, 6),
            "cost_input_total": round(sum(c["cost"]["input_usd"] for c in self.conversations), 6),
            "cost_output_total": round(sum(c["cost"]["output_usd"] for c in self.conversations), 6)
        }
    
    def get_by_phone(self, phone: str) -> list:
        """Get all interactions for a phone number."""
        return [c for c in self.conversations if c["phone"] == phone]
    
    def get_by_date(self, date: str) -> list:
        """
        Get interactions for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of interactions on that date
        """
        return [c for c in self.conversations if c["date"] == date]
    
    def get_by_date_range(self, start_date: str, end_date: str) -> list:
        """
        Get interactions in a date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of interactions in range
        """
        return [
            c for c in self.conversations
            if start_date <= c["date"] <= end_date
        ]
    
    def get_last_n(self, n: int) -> list:
        """Get last N interactions."""
        return self.conversations[-n:]
    
    def export_csv(self, output_file: str = "conversation_export.csv") -> None:
        """
        Export logs to CSV file.
        
        Args:
            output_file: Output CSV path
        """
        import csv
        
        if not self.conversations:
            print("No conversations to export")
            return
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "id", "timestamp", "phone", "user_message", "ai_response",
                    "model", "tokens_total", "cost_total_usd"
                ]
            )
            writer.writeheader()
            
            for c in self.conversations:
                writer.writerow({
                    "id": c["id"],
                    "timestamp": c["timestamp"],
                    "phone": c["phone"],
                    "user_message": c["user_message"],
                    "ai_response": c["ai_response"],
                    "model": c["model"],
                    "tokens_total": c["tokens"]["total"],
                    "cost_total_usd": c["cost"]["total_usd"]
                })
        
        print(f"✅ Exported to {output_file}")
    
    def print_stats(self) -> None:
        """Print formatted statistics."""
        stats = self.get_stats()
        
        print("\n" + "=" * 70)
        print("📊 Conversation Statistics")
        print("=" * 70)
        print(f"\n Total Interactions: {stats['total_interactions']}")
        print(f"   Total Tokens Used: {stats['total_tokens']:,}")
        print(f"   Avg Tokens/Interaction: {stats['avg_tokens_per_interaction']}")
        print(f"\n   Total Cost: ${stats['total_cost_usd']:.6f}")
        print(f"   Avg Cost/Interaction: ${stats['avg_cost_per_interaction']:.6f}")
        print(f"   Cost (Input): ${stats['cost_input_total']:.6f}")
        print(f"   Cost (Output): ${stats['cost_output_total']:.6f}")
        print("\n" + "=" * 70)
    
    def print_recent(self, n: int = 5) -> None:
        """Print recent conversations."""
        recent = self.get_last_n(n)
        
        if not recent:
            print("No conversations to display")
            return
        
        print("\n" + "=" * 70)
        print(f"📝 Last {n} Conversations")
        print("=" * 70)
        
        for c in recent:
            print(f"\n[{c['id']}] {c['timestamp']}")
            print(f"  Phone: {c['phone']}")
            print(f"  User: {c['user_message'][:50]}...")
            print(f"  AI: {c['ai_response'][:50]}...")
            print(f"  Cost: ${c['cost']['total_usd']:.6f} ({c['tokens']['total']} tokens)")
        
        print("\n" + "=" * 70)


# Example usage for testing
if __name__ == "__main__":
    logger = ConversationLogger()
    
    # Log some test interactions
    logger.log_interaction(
        phone="5511999999999",
        user_message="Olá, preciso fazer check-in",
        ai_response="Bem-vindo ao hotel! Para fazer check-in, preciso do seu nome e número de reserva.",
        tokens_input=15,
        tokens_output=25,
        model="gpt-3.5-turbo",
        metadata={"source": "whatsapp"}
    )
    
    logger.log_interaction(
        phone="5511999999999",
        user_message="Meu nome é João Silva, reserva 12345",
        ai_response="Perfeito João! Seu check-in foi confirmado! Você está no quarto 305. Bom descanso!",
        tokens_input=20,
        tokens_output=30,
        model="gpt-3.5-turbo",
        metadata={"source": "whatsapp"}
    )
    
    # Show stats
    logger.print_stats()
    logger.print_recent(2)
    
    # Export to CSV
    logger.export_csv()
