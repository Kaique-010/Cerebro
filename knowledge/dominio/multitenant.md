# Multi Tenant

O sistema utiliza slug para identificar o tenant.

A resolução do banco deve ocorrer por utilitário central.
Queries devem usar db_alias explícito que chamamos de banco.
Empresa e filial podem vir de sessão ou headers.
Normalmente usamos o prefixo de _empr, e _fili para identificar empresas e filiais
PEga sempre empresa e filial da Sessão ou Headers.
