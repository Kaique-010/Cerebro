# Services

Toda regra de negócio relevante deve ficar em services.

Views devem:

- ser finas
- sempre usar CBVs
- receber request
- validar entrada
- chamar service
- devolver resposta
- não ter lógica de negócio

Services devem:

- concentrar regra
- usar transação quando necessário
- receber dependências e parâmetros explícitos
- criar serviços baseados nos modelos e regras explicitas
- evitar duplicação de código
