from app.application.use_cases.checkin_via_whatsapp import CheckInViaWhatsAppUseCase
from app.application.dto.checkin_request_dto import CheckinRequestDTO
from app.infrastructure.persistence.memory.reservation_repository_memory import ReservationRepositoryMemory
from app.infrastructure.cache.redis_repository import RedisRepository
from app.domain.entities.reservation.reservation import Reservation
from app.domain.value_objects.phone_number import PhoneNumber
from app.domain.entities.reservation.reservation_status import ReservationStatus

def test_checkin_with_cache():
    # Configurar o repositório de reservas e o cache
    reservation_repository = ReservationRepositoryMemory()
    cache_repository = RedisRepository()
    
    # Criar uma reserva e armazená-la no repositório
    reservation = Reservation(reservation_id="1", guest_name="Guilherme de Jesus Silva", guest_phone=PhoneNumber("5561998776092"), status=ReservationStatus.CHECKED_IN)
    reservation_repository.save(reservation)
    
    # Criar o caso de uso
    checkin_use_case = CheckInViaWhatsAppUseCase(reservation_repository, cache_repository)
    
    # Criar o DTO de requisição
    request_dto = CheckinRequestDTO(phone="5561998776092")
    
    # Executar o caso de uso pela primeira vez (sem cache)
    response_dto_1 = checkin_use_case.execute(request_dto)
    print(response_dto_1.message)  # Deve indicar que o check-in foi feito com sucesso
    
    # Executar o caso de uso pela segunda vez (com cache)
    response_dto_2 = checkin_use_case.execute(request_dto)
    print(response_dto_2.message)  # Deve indicar que a reserva foi encontrada no cache e o check-in foi feito com sucesso
    
### Esse teste salva algum valor dentro do Redis Cloud ? Se sim, onde posso ver ?
# Sim, esse teste salva um valor dentro do Redis Cloud. Você pode ver os valores salvos acessando o painel de controle do Redis Cloud, onde você pode visualizar as chaves e os valores armazenados no seu banco de dados Redis. Procure pela chave correspondente ao número de telefone utilizado no teste (neste caso, "1234567890") para verificar se a reserva foi armazenada corretamente no cache do Redis.
# Coloco o número lá e não aparece nada, tem algum comando para listar as chaves do Redis Cloud ?
# Para listar as chaves armazenadas no Redis Cloud, você pode usar o comando `KEYS *` no terminal do Redis. Este comando irá retornar todas as chaves armazenadas no banco de dados Redis. Certifique-se de estar conectado ao banco de dados correto e de ter as permissões adequadas para executar esse comando. Se você estiver usando um cliente Redis, como o Redis CLI, basta digitar `KEYS *` e pressionar Enter para ver a lista de chaves disponíveis.

### O que aparece quando eu executo o comando `KEYS *` no Redis Cloud ?
# Quando você executa o comando `KEYS *` no Redis Cloud, ele retorna uma lista de todas as chaves armazenadas no banco de dados Redis. Cada chave representa um item de dados que foi armazenado, e pode ser associada a um valor específico.
# No contexto do teste que você executou, você deve ver uma chave correspondente ao número de telefone utilizado no teste (neste caso, "1234567890"), indicando que a reserva foi armazenada no cache do Redis. Se não houver chaves listadas, isso pode indicar que o valor não foi salvo corretamente ou que você está conectado ao banco de dados errado.

### Não veio nada correspondente ao numero 1234567890, e agora ?
# Se não apareceu nenhuma chave correspondente ao número "1234567890" após executar o comando `KEYS *`, isso pode indicar que o valor não foi salvo corretamente no Redis.
# Verifique se o código do caso de uso `CheckInViaWhatsAppUseCase` está realmente chamando o método `set` do `cache_repository` para armazenar a reserva no cache do Redis. Além disso, certifique-se de que a conexão com o Redis Cloud está configurada corretamente e que não há erros de conexão ou autenticação.
# Você também pode adicionar logs ou prints no código para verificar se o método `set` está sendo chamado e se os dados estão sendo passados corretamente para o Redis. Se o problema persistir, revise a configuração do Redis Cloud e as credenciais de acesso para garantir que tudo esteja configurado corretamente.