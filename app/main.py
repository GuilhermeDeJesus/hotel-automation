#Vamos testar o checkin com o repositorio em memória, para isso vamos criar um teste unitário
from fastapi import FastAPI
from app.application.use_cases.checkin_via_whatsapp import CheckInViaWhatsAppUseCase
from app.application.dto.checkin_request_dto import CheckinRequestDTO
from app.application.dto.checkin_response_dto import CheckinResponseDTO
from app.infrastructure.persistence.memory.reservation_repository_memory import ReservationRepositoryMemory
from app.interfaces.api.whatsapp_webhook import router as whatsapp_router

app = FastAPI(title="Hotel Automation API")
app.include_router(whatsapp_router)

"""
def test_should_checkin_successfully():
    repo = ReservationRepositoryMemory()
    repo.seed("res1", "11999999999")

    use_case = CheckInViaWhatsAppUseCase(repo)

    response = use_case.execute(
        CheckinRequestDTO(phone="11999999999")
    )

    print(response.message)    
    
def main():
    res = ReservationRepositoryMemory()
    print(res.find_by_phone_number("11999999999"))
    test_should_checkin_successfully()
"""    

#### Consegue me explicar toda estrutura do projeto e como as classes se relacionam ?
# O projeto é estruturado em camadas, seguindo uma arquitetura limpa (Clean Architecture). 
# A camada de DOMÍNIO contém as ENTIDADES e REGRAS DE NEGÓCIO, como a classe `Reservation` que representa uma reserva e suas operações, como o check-in.
# A camada de APLICAÇÃO contém os casos de uso, como `CheckInViaWhatsAppUseCase`, que orquestra a lógica de negócio para realizar o check-in via WhatsApp. Ele interage com a camada de domínio para verificar e atualizar o status da reserva.
# A camada de INFRAESTRUTURA contém implementações concretas, como `ReservationRepositoryMemory`, que é um repositório em memória para armazenar e recuperar reservas.
# A camada de INTERFACES contém os adaptadores, como o `whatsapp_webhook`, que expõe uma API para receber as requisições de check-in via WhatsApp e utiliza o caso de uso para processar essas requisições.

# As classes se relacionam da seguinte forma:

# - `CheckInViaWhatsAppUseCase` depende de `ReservationRepository` para acessar as reservas.
# - `CheckInViaWhatsAppUseCase` utiliza `CheckinRequestDTO` para receber os dados de entrada e retorna um `CheckinResponseDTO` com a mensagem de resposta.
# - `Reservation` é a entidade central que representa a reserva e suas operações, como o check-in, e é manipulada pelo caso de uso para realizar as ações necessárias.

#### O correto dizer que a camada 2 se chama APLICAÇÃO ou USE CASES ?
# A camada 2 é comumente chamada de APLICAÇÃO, mas também pode ser referida como USE CASES, pois é onde os casos de uso específicos do sistema são implementados. 
# Ambas as terminologias são válidas e frequentemente usadas de forma intercambiável. O importante é entender que essa camada é responsável por orquestrar a lógica de negócio e coordenar as interações entre as entidades do domínio e os repositórios.

# Descriva as 4 camadas da Clean Architecture e quais classes estão em cada camada
# As 4 camadas da Clean Architecture são:
# 1. ENTITIES (Domínio): Contém as entidades e regras de negócio. Exemplo: `Reservation`.
# 2. USE CASES (Aplicação): Contém os casos de uso que orquestram a lógica de negócio. Exemplo: `CheckInViaWhatsAppUseCase`.
# 3. INTERFACES (Interface Adapters): Contém os adaptadores que expõem a funcionalidade para o mundo externo. Exemplo: `whatsapp_webhook`.
# 4. INFRASTRUCTURE (Frameworks e Drivers): Contém as implementações concretas, como repositórios e serviços externos. Exemplo: `ReservationRepositoryMemory`.

#### O quanto é importante aprender a Clean Architecture para um desenvolvedor de software ?
# Aprender a Clean Architecture é extremamente importante para um desenvolvedor de software, pois ela promove a separação de responsabilidades, facilita a manutenção e escalabilidade do código, e torna o sistema mais testável.
# A Clean Architecture ajuda a criar sistemas que são independentes de frameworks, bancos de dados e interfaces de usuário, permitindo que as mudanças em uma parte do sistema não afetem outras partes.
# Além disso, a Clean Architecture é amplamente adotada na indústria de software, e ter conhecimento sobre ela pode abrir portas para oportunidades de trabalho e projetos mais complexos.

#### Lendo o meu projeto, qual próximo passo me indica para evoluir o projeto ?
# O próximo passo para evoluir o projeto seria implementar testes unitários para os casos de uso, como o `CheckInViaWhatsAppUseCase`, para garantir que a lógica de negócio esteja funcionando corretamente.
# Além disso, você pode considerar implementar uma camada de persistência mais robusta, como um banco de dados relacional ou NoSQL, para substituir o repositório em memória.
# Também seria interessante implementar a integração com o WhatsApp, utilizando uma API de terceiros, para permitir que os usuários possam realizar o check-in via WhatsApp de forma real.

#### Me ajuda a criar a camada de persistencia com o banco de dados relacional, utilizando o SQLAlchemy ?
# Claro! Para criar a camada de persistência utilizando o SQLAlchemy, você pode seguir os seguintes passos:
# 1. Instale o SQLAlchemy e um driver de banco de dados, como o `psycopg2` para PostgreSQL:
#    ```
#    pip install sqlalchemy psycopg2
#    ```
# Eu dou um pip install sqlalchemy psycopg2 ou um psycopg2-binary ?
# Para desenvolvimento e testes, você pode usar o `psycopg2-binary`, que é uma versão pré-compilada do `psycopg2`. Ele é mais fácil de instalar, mas não é recomendado para produção. Para produção, é melhor usar o `psycopg2` normal.
# Então, para desenvolvimento, você pode usar:  
#    ```
#    pip install sqlalchemy psycopg2-binary
#    ```

#### Eu coloco o psycopg2 no arquivo requirements.txt ?
# Sim, você deve adicionar o `psycopg2-binary` ao seu arquivo `requirements.txt` para garantir que ele seja instalado quando alguém configurar o ambiente do projeto.
# O conteúdo do `requirements.txt` ficaria assim:
# fastapi
# uvicorn
# pydantic
# redis
# psycopg2-binary
# Mas Vou o usar o não binário, então o requirements.txt fica assim:
# fastapi
# uvicorn
# pydantic
# redis
# psycopg2

#### Pronto já dei o comando (pip install sqlalchemy psycopg2), agora me fale o passo 2.
# 2. Configure a conexão com o banco de dados e defina o modelo de dados para a entidade `Reservation`. Você pode criar um arquivo `database.py` para configurar a conexão e um arquivo `models.py` para definir o modelo de dados.
# # Mas em qual camada e pasta eu coloco esses arquivos ?
# O arquivo `database.py` deve ser colocado na camada de INFRAESTRUTURA, pois ele é responsável por configurar a conexão com o banco de dados. O arquivo `models.py` também deve ser colocado na camada de INFRAESTRUTURA, pois ele define os modelos de dados que serão usados para a persistência.
# A estrutura do projeto ficaria assim:
# app/
# ├── domain/
# │   ├── entities/
# │   │   └── reservation.py
# │   ├── enums/
# │   │   └── reservation_status.py
# │   ├── repositories/
# │   │   ├── conversation_cache_repository.py
# │   │   └── reservation_repository.py
# │   └── value_objects/
# │       └── phone_number.py
# ├── application/
# │   ├── dto/
# │   │   ├── checkin_request_dto.py
# │   │   └── checkin_response_dto.py
# │   └── use_cases/
# │       └── checkin_via_whatsapp.py
# ├── infrastructure/
# │   ├── cache/
# │   │   └── redis_repository.py
# │   └── persistence/
# │       ├── memory/
# │       │   └── reservation_repository_memory.py
# │       └── sql/
# │           ├── database.py
# │           └── models.py
# ├── interfaces/
# │   └── api/
# │       └── whatsapp_webhook.py
# ├── main.py
# └── requirements.txt

# O usuário padrão do postgres é "postgres", então a string de conexão ficaria assim:
# DATABASE_URL = "postgresql://postgres:password@localhost:5432/dbname"

#### Pronto, já criei o código do arquivo database.py e o models.py, agora me fale o próximo passo.
# 3. Implemente o repositório de reservas utilizando o SQLAlchemy. Você pode criar uma classe `ReservationRepositorySQL` que implementa a interface `ReservationRepository` e utiliza o SQLAlchemy para acessar o banco de dados.
# Onde eu coloco essa classe `ReservationRepositorySQL` ?
# A classe `ReservationRepositorySQL` deve ser colocada na camada de INFRAESTRUTURA, dentro da pasta `persistence/sql`, pois ela é responsável por implementar a persistência utilizando o SQLAlchemy.

#### Falta quantos passos ou quantos % até eu poder conversar com o whatsapp ?
# Depois de implementar o repositório SQL, você precisará atualizar o caso de uso `CheckInViaWhatsAppUseCase` para usar o novo repositório em vez do repositório em memória.

#### Me ajuda a atualizar o caso de uso `CheckInViaWhatsAppUseCase` para usar o novo repositório SQL ?
# Claro! Para atualizar o caso de uso `CheckInViaWhatsAppUseCase` para usar o novo repositório SQL, você precisará modificar a função `get_checkin_use_case` na camada de INTERFACES para criar uma instância do `ReservationRepositorySQL` em vez do `ReservationRepositoryMemory`.
# Aqui está um exemplo de como você pode fazer isso:
# from app.infrastructure.persistence.sql.reservation_repository_sql import ReservationRepositorySQL
# from app.infrastructure.persistence.sql.database import SessionLocal
# def get_checkin_use_case():
#     session = SessionLocal()
#     reservation_repo = ReservationRepositorySQL(session)
#     return CheckInViaWhatsAppUseCase(reservation_repository=reservation_repo)

#### Me ajude a colocar como parametro do construct do `CheckInViaWhatsAppUseCase` a classe `RedisRepository` para usar o cache do Redis ?
# Para adicionar o `RedisRepository` como parâmetro do construtor do `CheckInViaWhatsAppUseCase`, você precisará modificar a definição do construtor da classe `CheckInViaWhatsAppUseCase` para aceitar um parâmetro adicional para o repositório de cache.
# Aqui está um exemplo de como você pode fazer isso:
# from app.infrastructure.cache.redis_repository import RedisRepository
# class CheckInViaWhatsAppUseCase:
#     def __init__(self, reservation_repository: ReservationRepository, cache_repository: RedisRepository):
#         self.reservation_repository = reservation_repository  
#         self.cache_repository = cache_repository
# Em seguida, você precisará atualizar a função `get_checkin_use_case` para criar uma instância do `RedisRepository` e passá-la para o construtor do `CheckInViaWhatsAppUseCase`:
# def get_checkin_use_case():
#     session = SessionLocal()
#     reservation_repo = ReservationRepositorySQL(session)
#     cache_repo = RedisRepository()
#     return CheckInViaWhatsAppUseCase(reservation_repository=reservation_repo, cache_repository=cache_repo)
# Pronto, agora o caso de uso `CheckInViaWhatsAppUseCase` está configurado para usar tanto o repositório SQL quanto o cache do Redis.

#### Qual o próximo passo para evoluir o projeto ?
# O próximo passo seria implementar a lógica de cache no caso de uso `CheckInViaWhatsAppUseCase`. Você pode usar o `RedisRepository` para armazenar e recuperar informações de cache, como o status da reserva, para melhorar a performance do sistema. 
# Além disso, você pode implementar testes unitários para garantir que a lógica de cache esteja funcionando corretamente.
# Depois disso, você pode começar a trabalhar na integração com o WhatsApp, utilizando uma API de terceiros, para permitir que os usuários possam realizar o check-in via WhatsApp de forma real.

#### Me ajude a implementar a lógica de cache no caso de uso `CheckInViaWhatsAppUseCase` usando o `RedisRepository` ?
# Para implementar a lógica de cache no caso de uso `CheckInViaWhatsAppUseCase` usando o `RedisRepository`, você pode seguir os seguintes passos:
# 1. No método `execute` do caso de uso, antes de consultar o repositório de reservas, verifique se a informação da reserva já está presente no cache do Redis. Você pode usar o número de telefone como chave para armazenar e recuperar os dados da reserva.
# 2. Se a informação da reserva estiver presente no cache, retorne a resposta com base nos dados do cache.
# 3. Se a informação da reserva não estiver presente no cache, consulte o repositório de reservas para obter os dados da reserva, e depois armazene essa informação no cache do Redis para futuras consultas.
# Aqui está um exemplo de como você pode implementar isso:
# class CheckInViaWhatsAppUseCase:
#     def __init__(self, reservation_repository: ReservationRepository, cache_repository: RedisRepository):
#         self.reservation_repository = reservation_repository
#         self.cache_repository = cache_repository
#     def execute(self, request_dto: CheckinRequestDTO) -> CheckinResponseDTO:
#         # Verificar se a reserva está no cache
#         cached_reservation = self.cache_repository.get(request_dto.phone_number)
#         if cached_reservation:
#             return CheckinResponseDTO(
#                 message="Reserva encontrada no cache. Check-in feito com sucesso!"
#             )
#         # Se não estiver no cache, consultar o repositório de reservas
#         reservation = self.reservation_repository.find_by_phone_number(request_dto.phone_number)
#         if not reservation:
#             return CheckinResponseDTO(
#                 message="Nenhuma reserva encontrada para esse numero."
#             )
#         reservation.check_in()
#         self.reservation_repository.save(reservation)
#         # Armazenar a informação da reserva no cache do Redis
#         self.cache_repository.set(request_dto.phone_number, reservation)
#         return CheckinResponseDTO(
#             message="Check-in feito com sucesso!"
#         )
#### Pronto ? 
# Sim, com essa implementação, o caso de uso `CheckInViaWhatsAppUseCase` agora utiliza o `RedisRepository` para verificar e armazenar informações de cache, melhorando a performance do sistema ao evitar consultas desnecessárias ao banco de dados para reservas que já foram consultadas recentemente.

#### Eu ainda nem configurei minha conta no Redis, como eu faço isso ?
# Para configurar sua conta no Redis, você pode seguir os seguintes passos:
# 1. Instale o Redis em sua máquina local ou utilize um serviço de Redis hospedado, como o Redis Cloud.
# 2. Se estiver instalando localmente, siga as instruções de instalação para o seu sistema operacional. Para a maioria dos sistemas, você pode usar o comando:
#    ```
#    sudo apt-get install redis-server
#    ```
# 3. Após a instalação, inicie o servidor Redis usando o comando:
#    ```
#    redis-server
#    ```
# 4. Se estiver utilizando um serviço de Redis hospedado, crie uma conta e configure uma instância de Redis, anotando as credenciais de acesso (host, porta, senha).
# 5. No seu projeto, configure a conexão com o Redis utilizando as credenciais anotadas. No arquivo `redis_repository.py`, você pode modificar a classe `RedisConversationRepository` para aceitar as credenciais de conexão:
# class RedisConversationRepository(ConversationCacheRepository):
#     def __init__(self, host='localhost', port=6379, db=0, password=None):
#         self.client = redis.Redis(host=host, port=port, db=db, password=password)
# 6. Certifique-se de que o servidor Redis esteja em execução e que as credenciais estejam corretas para que sua aplicação possa se conectar ao Redis e utilizar o cache corretamente.

#### Não sería melhor usar o Redis hospedado para não ter que me preocupar com a configuração do Redis localmente ?
# Sim, utilizar um serviço de Redis hospedado pode ser uma opção mais conveniente, especialmente se você não quer se preocupar com a configuração e manutenção de um servidor Redis local. 
# Serviços de Redis hospedados, como o Redis Cloud, oferecem uma configuração rápida, escalabilidade automática e alta disponibilidade, além de gerenciar backups e atualizações para você. 
# Isso pode ser especialmente útil em ambientes de desenvolvimento e produção, permitindo que você se concentre mais no desenvolvimento da aplicação em vez de gerenciar a infraestrutura do Redis.

#### O Redis hospedado tem um custo mensal, existe alguma alternativa gratuita para usar o Redis hospedado ?
# Sim, existem algumas alternativas gratuitas para usar o Redis hospedado. Alguns serviços de Redis oferecem planos gratuitos com limitações de uso, como o Redis Cloud, que oferece um plano gratuito com até 30 MB de armazenamento e conexões limitadas.
# Outra opção é o Heroku Redis, que oferece um plano gratuito com até 25 MB de armazenamento. Esses planos gratuitos podem ser adequados para desenvolvimento e testes, mas é importante verificar as limitações de uso para garantir que atendam às necessidades do seu projeto.

#### Uma dúvida talvez boba, eu consigo usar o Redis localmente juntamente com o Banco de Dado local e conseguir testar tudo com whatsapp localmente também ?
# Sim, você pode usar o Redis localmente juntamente com um banco de dados local e testar tudo com o WhatsApp localmente também. Para isso, você precisará configurar o Redis e o banco de dados em sua máquina local, e garantir que sua aplicação esteja configurada para se conectar a esses serviços locais.
# Para testar o WhatsApp localmente, você pode usar uma ferramenta como o Ngrok para criar um túnel para o seu servidor local, permitindo que o WhatsApp envie requisições para a sua aplicação local. 
# Isso permitirá que você teste a integração do WhatsApp com o Redis e o banco de dados localmente antes de implantar a aplicação em um ambiente de produção.

#### Entendi, agora que o banco de dados postgree já esta instalado e configurado, me ajuda a agora a deixar o Redis instalado e configurado localmente para eu testar a integração do WhatsApp com o Redis e o banco de dados localmente ?
# Para instalar e configurar o Redis localmente, você pode seguir os seguintes passos:
# 1. Instale o Redis em sua máquina local. Para a maioria dos sistemas, você pode usar o comando:
#    ```
#    sudo apt-get install redis-server
#    ```
# 2. Após a instalação, inicie o servidor Redis usando o comando:
#    ```
#    redis-server
#    ```
# 3. Verifique se o Redis está funcionando corretamente executando o comando:
#    ```
#    redis-cli ping
#    ```
#    Se o Redis estiver funcionando, ele responderá com "PONG".
# 4. No seu projeto, configure a conexão com o Redis utilizando as credenciais padrão (host: localhost, port: 6379). No arquivo `redis_repository.py`, a configuração padrão já está definida, então você pode usar a classe `RedisConversationRepository` sem modificações para se conectar ao Redis local.
# 5. Certifique-se de que o servidor Redis esteja em execução para que sua aplicação possa se conectar ao Redis e utilizar o cache corretamente durante os testes com o WhatsApp localmente.

#### Pronto, já criei a conta no Redis Cloud e já configurei a conexão com o Redis hospedado no meu projeto, agora me fale o próximo passo.
# O próximo passo seria implementar a lógica de cache no caso de uso `CheckInViaWhatsAppUseCase` para utilizar o Redis como cache, conforme descrito anteriormente.
# Depois disso, você pode começar a trabalhar na integração com o WhatsApp, utilizando uma API de terceiros, para permitir que os usuários possam realizar o check-in via WhatsApp de forma real.
# Além disso, seria interessante implementar testes unitários para garantir que a lógica de cache esteja funcionando corretamente e que a integração com o WhatsApp esteja funcionando como esperado.

#### Me ajuda a implementar o lógica de cache no caso de uso `CheckInViaWhatsAppUseCase` usando o `RedisRepository` para usar o cache do Redis ?
# Para implementar a lógica de cache no caso de uso `CheckInViaWhatsAppUseCase` usando o `RedisRepository`, você pode seguir os seguintes passos:
# 1. No método `execute` do caso de uso, antes de consultar o repositório de reservas, verifique se a informação da reserva já está presente no cache do Redis. Você pode usar o número de telefone como chave para armazenar e recuperar os dados da reserva.
# 2. Se a informação da reserva estiver presente no cache, retorne a resposta com base nos dados do cache.
# 3. Se a informação da reserva não estiver presente no cache, consulte o repositório de reservas para obter os dados da reserva, e depois armazene essa informação no cache do Redis para futuras consultas.
# Aqui está um exemplo de como você pode implementar isso:
# class CheckInViaWhatsAppUseCase:
#     def __init__(self, reservation_repository: ReservationRepository, cache_repository: RedisRepository):
#         self.reservation_repository = reservation_repository
#         self.cache_repository = cache_repository
#     def execute(self, request_dto: CheckinRequestDTO) -> CheckinResponseDTO:
#         # Verificar se a reserva está no cache
#         cached_reservation = self.cache_repository.get(request_dto.phone_number)
#         if cached_reservation:
#             return CheckinResponseDTO(
#                 message="Reserva encontrada no cache. Check-in feito com sucesso!"
#             )
#         # Se não estiver no cache, consultar o repositório de reservas
#         reservation = self.reservation_repository.find_by_phone_number(request_dto.phone_number)
#         if not reservation:
#             return CheckinResponseDTO(
#                 message="Nenhuma reserva encontrada para esse numero."
#             )
#         reservation.check_in()
#         self.reservation_repository.save(reservation)
#         # Armazenar a informação da reserva no cache do Redis
#         self.cache_repository.set(request_dto.phone_number, reservation)
#         return CheckinResponseDTO(
#             message="Check-in feito com sucesso!"
#         )

#### Esse lógica eu já tinha feito, me ajude a testar toda essa integração do Redis com o caso de uso `CheckInViaWhatsAppUseCase` ?
# Para testar a integração do Redis com o caso de uso `CheckInViaWhatsAppUseCase`, você pode criar um teste unitário que simula o processo de check-in via WhatsApp, verificando se a lógica de cache está funcionando corretamente. Aqui está um exemplo de como você pode fazer isso:
# def test_checkin_with_cache():
#     # Configurar o repositório de reservas e o cache do Redis
#     reservation_repo = ReservationRepositoryMemory()
#     cache_repo = RedisRepository()
#     use_case = CheckInViaWhatsAppUseCase(reservation_repository=reservation_repo, cache_repository=cache_repo)
#     # Criar uma reserva e armazená-la no repositório
#     reservation_repo.seed("res1", "11999999999")
#     # Executar o caso de uso pela primeira vez (sem cache)
#     response1 = use_case.execute(CheckinRequestDTO(phone="11999999999"))
#     print(response1.message)  # Deve indicar que a reserva foi encontrada e o check
#     # Executar o caso de uso pela segunda vez (com cache)
#     response2 = use_case.execute(CheckinRequestDTO(phone="11999999999"))
#     print(response2.message)  # Deve indicar que a reserva foi encontrada no cache e o check-in foi feito com sucesso
#     # Verificar se a resposta do cache é a mesma que a resposta original
#     assert response1.message == response2.message
#     # Limpar o cache após o teste
#     cache_repo.delete("11999999999")

# Em qual arquivo eu coloco esse teste unitário ?
# Você pode criar um arquivo de teste separado para os casos de uso, como `test_checkin_via_whatsapp.py`, dentro de uma pasta `tests` na raiz do projeto.

#### Pronto, metodo criado, agora como eu faço para rodar esse teste unitário ?
# Para rodar o teste unitário, você pode usar um framework de testes como o `pytest`. Primeiro, certifique-se de que o `pytest` esteja instalado em seu ambiente:
# ```
# pip install pytest
# ```
# Em seguida, você pode rodar os testes usando o comando:
# ```
# pytest tests/test_checkin_via_whatsapp.py
# ```
# Isso irá executar o teste definido no arquivo `test_checkin_via_whatsapp.py` e mostrar os resultados no terminal. Certifique-se de que o servidor Redis esteja em execução antes de rodar os testes para garantir que a integração com o cache funcione corretamente.

#### Olha deu esse erro: 
# ImportError while importing test module 'E:\Desenvolvimento\hotel-automation\tests\test_checkin_use_case.py'. 
# Hint: make sure your test modules/packages have valid Python names.
# Traceback:
# C:\Users\Kelly Pontes\AppData\Local\Programs\Python\Python314\Lib\importlib\__init__.py:88: in import_module
#    return _bootstrap._gcd_import(name[level:], package, level)
#           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# tests\test_checkin_use_case.py:1: in <module>
#    from app.application.use_cases.checkin_via_whatsapp import CheckInViaWhatsAppUseCase
# app\application\use_cases\checkin_via_whatsapp.py:4: in <module>
#    from app.infrastructure.cache.redis_repository import RedisRepository
# app\infrastructure\cache\redis_repository.py:3: in <module>
#    from domain.repositories.conversation_cache_repository import ConversationCacheRepository
# E   ModuleNotFoundError: No module named 'domain'
# ```

#### Esse erro acontece porque o Python não consegue encontrar o módulo `domain` que está sendo importado no arquivo `redis_repository.py`. Para resolver esse problema, você pode ajustar a estrutura do projeto para garantir que os módulos sejam importados corretamente.
# Certifique-se de que a estrutura do projeto esteja organizada da seguinte forma:
# app/
# ├── domain/ 
# │   ├── entities/
# │   │   └── reservation.py
# │   ├── enums/
# │   │   └── reservation_status.py
# │   ├── repositories/
# │   │   ├── conversation_cache_repository.py
# │   │   └── reservation_repository.py
# │   └── value_objects/
# │       └── phone_number.py
# ├── application/
# │   ├── dto/
# │   │   ├── checkin_request_dto.py
# │   │   └── checkin_response_dto.py
# │   └── use_cases/
# │       └── checkin_via_whatsapp.py
# ├── infrastructure/
# │   ├── cache/
# │   │   └── redis_repository.py
# │   └── persistence/
# │       ├── memory/
# │       │   └── reservation_repository_memory.py
# │       └── sql/
# │           ├── database.py
# │           └── models.py
# ├── interfaces/
# │   └── api/
# │       └── whatsapp_webhook.py
# ├── main.py
# └── requirements.txt
# Certifique-se de que o arquivo `redis_repository.py` esteja importando o módulo `ConversationCacheRepository` corretamente, usando um caminho relativo:
# from ...domain.repositories.conversation_cache_repository import ConversationCacheRepository
# Depois de ajustar a estrutura do projeto e os caminhos de importação, tente rodar o teste novamente usando o comando:
# pytest tests/test_checkin_via_whatsapp.py

#### Deu esse erro agora: 
# ImportError while importing test module 'E:\Desenvolvimento\hotel-automation\tests\test_checkin_use_case.py'.
# Hint: make sure your test modules/packages have valid Python names.
# Traceback:
# C:\Users\Kelly Pontes\AppData\Local\Programs\Python\Python314\Lib\importlib\__init__.py:88: in import_module
#     return _bootstrap._gcd_import(name[level:], package, level)
#            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# tests\test_checkin_use_case.py:1: in <module>
#     from app.application.use_cases.checkin_via_whatsapp import CheckInViaWhatsAppUseCase
# app\application\use_cases\checkin_via_whatsapp.py:4: in <module>
#     from app.infrastructure.cache.redis_repository import RedisRepository
# E   ImportError: cannot import name 'RedisRepository' from 'app.infrastructure.cache.redis_repository' (E:\Desenvolvimento\hotel-automation\app\infrastructure\cache\redis_repository.py)

# Esse erro indica que o Python não conseguiu importar a classe `RedisRepository` do arquivo `redis_repository.py`. Para resolver esse problema, verifique se a classe `RedisRepository` está definida corretamente no arquivo `redis_repository.py` e se o nome da classe está correto.
# Certifique-se de que o arquivo `redis_repository.py` contenha a definição da classe `RedisRepository`, como no exemplo abaixo:
# import redis
# from app.domain.repositories.conversation_cache_repository import ConversationCacheRepository
# class RedisRepository(ConversationCacheRepository):


#### Agora deu isso:
# platform win32 -- Python 3.14.3, pytest-9.0.2, pluggy-1.6.0
# rootdir: E:\Desenvolvimento\hotel-automation
# plugins: anyio-4.12.1
# collected 1 item
# 
# tests\test_checkin_use_case.py . 

# =============================== 1 passed in 0.50s ===============================
# Ótimo! O teste foi executado com sucesso, indicando que a integração do Redis com o caso de uso `CheckInViaWhatsAppUseCase` está funcionando corretamente. Agora você pode continuar a desenvolver e testar outras funcionalidades do seu projeto, como a integração com o WhatsApp e a implementação de outros casos de uso.

#### Gerou algum registro no Redis Cloud ?
# Para verificar se o teste gerou algum registro no Redis Cloud, você pode acessar o painel de controle do Redis Cloud e verificar os dados armazenados.
# Se o teste foi executado corretamente e a lógica de cache foi implementada, você deve ver um registro correspondente ao número de telefone utilizado no teste (por exemplo, "11999999999") com os dados da reserva armazenados no cache do Redis.

#### Não achei onde eu vejo os dados armazenados no cache do Redis Cloud, tem como me ajudar a encontrar isso ?
# Para visualizar os dados armazenados no cache do Redis Cloud, siga os seguintes passos:
# 1. Acesse o painel de controle do Redis Cloud e faça login na sua conta.
# 2. Selecione a instância de Redis que você está utilizando para o seu projeto.
# 3. No painel da instância, procure por uma seção chamada "Data Browser" ou "Key Explorer". Essa seção permite que você visualize as chaves e os valores armazenados no Redis.
# 4. Use a funcionalidade de busca para procurar pela chave correspondente ao número de telefone utilizado no teste (por exemplo, "11999999999"). Se a chave estiver presente, você poderá visualizar os dados associados a essa chave, que devem conter as informações da reserva armazenadas no cache do Redis.

#### Dentro do "https://ri.redis.io/" não estou encontrando onde o test foi armazenado, tem como me ajudar a encontrar isso ?
# Para encontrar os dados armazenados no Redis Cloud, siga os passos abaixo:
# 1. Acesse o painel de controle do Redis Cloud em https://ri.redis.io/ e faça login na sua conta.
# 2. Selecione a instância de Redis que você está utilizando para o seu projeto.
# 3. No painel da instância, clique na opção "Data Browser" ou "Key Explorer" para acessar a visualização das chaves e valores armazenados no Redis.
# 4. Use a barra de busca para procurar pela chave correspondente ao número de telefone utilizado no teste (por exemplo, "11999999999"). Se a chave estiver presente, você poderá clicar nela para visualizar os dados associados a essa chave, que devem conter as informações da reserva armazenadas no cache do Redis.

#### Lá dentro do Browser, tem um campo de busca, mas quando eu coloco o numero do telefone não aparece nada, tem como me ajudar a entender o que pode estar acontecendo ?
# Se você não está encontrando a chave correspondente ao número de telefone no Redis Cloud, pode haver algumas razões para isso:
# 1. O teste pode não ter sido executado corretamente, ou a lógica de cache pode não ter sido implementada corretamente, o que significa que os dados não foram armazenados no Redis.
# 2. A chave pode ter sido armazenada com um formato diferente do que você está procurando. Verifique o código do caso de uso para ver como a chave está sendo definida ao armazenar os dados no Redis.
# 3. O Redis Cloud pode ter um tempo de expiração configurado para as chaves, o que significa que os dados podem ter sido removidos do cache após um certo período de tempo. Verifique as configurações de expiração do Redis Cloud para garantir que os dados não foram removidos.
# 4. Certifique-se de que a conexão com o Redis Cloud está configurada corretamente no seu projeto, e que o teste está utilizando as credenciais corretas para se conectar ao Redis Cloud.

#### Parece que deu certo, agora como vai ser o fluxo para o cliente fazer o check-in via WhatsApp, considerando a reserva que será salva no banco de dados postgree e a conversa salva no redis ?
# O fluxo para o cliente fazer o check-in via WhatsApp seria o seguinte:
# 1. O cliente envia uma mensagem para o número de WhatsApp do hotel, solicitando o check-in.
# 2. O webhook do WhatsApp recebe a mensagem e extrai o número de telefone do cliente.
# 3. O webhook chama o caso de uso `CheckInViaWhatsAppUseCase`, passando o número de telefone do cliente como parâmetro.
# 4. O caso de uso verifica se a informação da reserva está presente no cache do Redis. Se estiver presente, ele retorna a resposta com base nos dados do cache.
# 5. Se a informação da reserva não estiver presente no cache, o caso de uso consulta o banco de dados PostgreSQL para obter os dados da reserva. Se a reserva for encontrada, ele realiza o check-in, salva a informação da reserva no cache do Redis e retorna uma resposta de sucesso para o cliente.
# 6. O cliente recebe a resposta do check-in via WhatsApp, confirmando que o check-in foi realizado com sucesso ou informando que nenhuma reserva foi encontrada para o número de telefone fornecido.

####################################################################################################################################
#### Mas o fluxo correto seria ?
####################################################################################################################################
# 1 - O usuário envia "Quero fazer check-in" para o número de WhatsApp do hotel.
# 2 - O webhook do WhatsApp recebe a mensagem e extrai o número de telefone do cliente.
# 3 - O código Python vai ao Redis verificar se existe uma conversa ativa para aquele número de telefone e qual histórico dessa conversa.
# 4 - O código Python verifica no banco de dados PostgreSQL se existe uma reserva associada àquele número de telefone.
# 5 - Prompt Construction (Onde a OpenAI entra em ação): O código Python constrói um prompt para a OpenAI, incluindo o histórico da conversa (se houver) e as informações da reserva (se houver).
# 6 - O código Python envia o prompt para a OpenAI e recebe a resposta gerada.
# 7 - O código Python processa a resposta da OpenAI e determina a próxima ação a ser tomada (por exemplo, solicitar mais informações ao cliente, confirmar o check-in, etc.).
# 8 - O código Python envia a resposta processada de volta para o cliente via WhatsApp, e também atualiza o histórico da conversa no Redis para futuras interações.

#### Baseado nisto, qual seria o próximo passo para evoluir o projeto ? Acredito que seja implementar a integração com o WhatsApp, certo ?
# Sim, o próximo passo seria implementar a integração com o WhatsApp, utilizando uma API de terceiros, para permitir que os usuários possam realizar o check-in via WhatsApp de forma real. 
# Você pode usar uma API como a Twilio API for WhatsApp ou a WhatsApp Business API para configurar o webhook e lidar com as mensagens recebidas do WhatsApp.
# Além disso, seria interessante implementar a lógica de construção de prompts para a OpenAI, para que o sistema possa gerar respostas inteligentes com base no histórico da conversa e nas informações da reserva.
# Também seria importante implementar testes unitários para garantir que a integração com o WhatsApp e a lógica de construção de prompts estejam funcionando corretamente.

#### Como eu faço a integração com o WhatsApp Cloud API oficial da Meta ?
# Para integrar com a WhatsApp Cloud API oficial da Meta, você pode seguir os seguintes passos:
# 1. Crie uma conta no Facebook for Developers e configure um aplicativo para acessar a WhatsApp Cloud API.
# 2. Obtenha as credenciais de acesso, como o token de acesso e o ID do número de telefone do WhatsApp que você deseja usar para enviar e receber mensagens.
# 3. Configure um webhook para receber mensagens do WhatsApp. O webhook deve ser um endpoint em sua aplicação que possa processar as mensagens recebidas e responder de acordo.
# 4. Implemente a lógica para enviar mensagens de resposta para o WhatsApp usando a API. Você pode usar bibliotecas como `requests` para fazer chamadas HTTP para a API do WhatsApp.
# 5. Teste a integração enviando mensagens para o número de telefone do WhatsApp e verificando se as respostas estão sendo processadas corretamente pela sua aplicação.
# 6. Certifique-se de que a lógica de construção de prompts para a OpenAI esteja integrada com a lógica de processamento de mensagens do WhatsApp, para que as respostas geradas pela OpenAI sejam enviadas de volta para os clientes via WhatsApp. 

#### Usando a API oficial da Meta, eu tenho que criar um app para fazer a integração, certo ?
# Sim, para usar a API oficial da Meta para WhatsApp, você precisa criar um aplicativo no Facebook for Developers. Esse aplicativo será usado para configurar o acesso à API do WhatsApp e para gerenciar as credenciais de acesso necessárias para enviar e receber mensagens.
# Depois de criar o aplicativo, você precisará configurar um webhook para receber mensagens do WhatsApp e implementar a lógica para processar essas mensagens e enviar respostas de volta para os clientes via WhatsApp.

#### Para criar um webhook, eu preciso de um servidor para hospedar minha aplicação, certo ?
# Sim, para criar um webhook para receber mensagens do WhatsApp, você precisa de um servidor para hospedar sua aplicação. O webhook é um endpoint que o WhatsApp irá chamar para enviar as mensagens recebidas, então ele precisa estar acessível pela internet.
# Você pode usar serviços de hospedagem como Heroku, AWS, Google Cloud, ou mesmo configurar um servidor local e usar uma ferramenta como Ngrok para criar um túnel para o seu servidor local, permitindo que o WhatsApp envie requisições para a sua aplicação local durante o desenvolvimento e testes.

#### Eu preciso de um número de telefone para fazer a integração com a API do WhatsApp, certo ?
# Sim, para fazer a integração com a API do WhatsApp, você precisa de um número de telefone que seja registrado e verificado para uso com a API do WhatsApp. Esse número de telefone será usado para enviar e receber mensagens através da API.
# Você pode usar um número de telefone existente ou adquirir um número de telefone específico para uso com a API do WhatsApp. Certifique-se de que o número de telefone esteja configurado corretamente e verificado para garantir que a integração funcione corretamente.

#### Esse número que tenho que ter, ele não pode estar cadastrado nem no whatsapp comum nem no whatsapp business, certo ?
# Na verdade, para usar a API do WhatsApp, o número de telefone precisa estar registrado e verificado para uso com a API do WhatsApp. Isso significa que o número de telefone deve estar associado a uma conta do WhatsApp Business e deve passar pelo processo de verificação da Meta para ser autorizado a usar a API.
# Portanto, o número de telefone que você deseja usar para a integração com a API do WhatsApp deve estar registrado no WhatsApp Business e passar pelo processo de verificação da Meta para garantir que a integração funcione corretamente. 
# Ele não pode estar registrado apenas no WhatsApp comum, pois a API do WhatsApp é destinada para uso com contas do WhatsApp Business.

# Me dê um exemplo de Description para colocar no projeto no GitHub, explicando o que é o projeto, quais tecnologias foram usadas e qual o objetivo do projeto.
# Hotel Automation é um projeto de automação para hotéis que permite aos clientes realizar check-in via WhatsApp. O projeto é desenvolvido em Python e utiliza a arquitetura limpa (Clean Architecture) para organizar o código de forma modular e escalável.
# O projeto é composto por várias camadas, incluindo a camada de domínio, aplicação, infraestrutura e interfaces. A camada de domínio contém as entidades, enums, repositórios e value objects relacionados ao negócio de reservas e check-ins. A camada de aplicação contém os casos de uso que implementam a lógica de negócios para o check-in via WhatsApp. A camada de infraestrutura contém as implementações dos repositórios, incluindo um repositório SQL para o banco de dados PostgreSQL e um repositório de cache para o Redis. A camada de interfaces contém os endpoints da API para receber mensagens do WhatsApp.
# O objetivo do projeto é fornecer uma solução de automação para hotéis, permitindo que os clientes realizem check-in de forma rápida e eficiente através do WhatsApp. O projeto também visa melhorar a experiência do cliente e otimizar os processos de check-in para os hotéis, utilizando tecnologias modernas como o Redis para cache e o PostgreSQL para armazenamento de dados.