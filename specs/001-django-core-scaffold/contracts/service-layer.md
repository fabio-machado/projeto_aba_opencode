# Contract: Service Layer Interface

**Version**: 1.0.0  
**Date**: 2026-04-23  
**Scope**: Define o padrão de interface para todos os arquivos `services.py` na aplicação.

---

## Interface Padrão

Todo service DEVE seguir este padrão:

```python
from typing import Any, Dict, List, Optional
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

class BaseService:
    """Base para todos os services."""
    
    def __init__(self) -> None:
        self._setup()
    
    def _setup(self) -> None:
        """Inicialização específica do service."""
        pass

class ExampleService(BaseService):
    """
    Service de exemplo demonstrando o padrão.
    
    Toda lógica de negócio reside aqui.
    Views apenas validam input e chamam métodos desta classe.
    """
    
    def create_record(
        self,
        user_id: UUID,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Cria um registro validando RLS e audit.
        
        Args:
            user_id: UUID do usuário autenticado
            data: Dados do registro a ser criado
            
        Returns:
            Dicionário com o registro criado
            
        Raises:
            ValueError: Se dados forem inválidos
            PermissionError: Se user_id não tiver permissão
        """
        # 1. Validar input
        # 2. Aplicar regras de negócio
        # 3. Executar operação (supabase-py, stripe, etc.)
        # 4. Registrar audit log
        # 5. Retornar resultado
        pass
```

## Regras Obrigatórias

1. **Type Hints**: Todo método público deve ter type hints em parâmetros e retorno
2. **Docstrings**: Todo método público deve ter docstring com Args, Returns, Raises
3. **No ORM Django**: Services de dados core devem usar `supabase-py`, não `django.db.models`
4. **UUID Serialization**: Converter `UUID` → `str(uuid)` antes de operações no SDK Supabase
5. **RLS Filter**: Sempre aplicar `eq("parent_id", str(user_id))` em queries de pacientes
6. **Audit Log**: Toda escrita em dados de pacientes deve chamar `AuditLogService.log()`
7. **Logging**: Usar `logging.getLogger(__name__)` para logs estruturados

## Anti-Patterns Proibidos

```python
# ❌ NUNCA faça isso em services.py:

# Lógica de UI ou HTTP
from django.http import HttpResponse
def create_record(self, request):  # Não receber Request
    ...

# ORM Django para dados core
from django.db import models
class Patient(models.Model):  # NÃO usar models.Model
    ...

# Queries sem filtro RLS
client.table("patients").select("*")  # SEMPRE filtrar por parent_id

# UUIDs não serializados
client.table("patients").insert({"id": uuid_obj})  # Use str(uuid_obj)
```
