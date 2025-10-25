# 🤝 Guia de Contribuição

Obrigado por considerar contribuir com o AllpFit Analytics! Este documento fornece diretrizes para contribuições.

## 📋 Índice

- [Código de Conduta](#código-de-conduta)
- [Como Contribuir](#como-contribuir)
- [Configuração do Ambiente](#configuração-do-ambiente)
- [Padrões de Código](#padrões-de-código)
- [Processo de Pull Request](#processo-de-pull-request)
- [Reportando Bugs](#reportando-bugs)
- [Sugerindo Features](#sugerindo-features)

## 🤝 Código de Conduta

Este projeto adere a um código de conduta. Ao participar, você concorda em manter um ambiente respeitoso e inclusivo.

## 🚀 Como Contribuir

### 1. Fork e Clone

```bash
# Fork no GitHub primeiro, depois:
git clone git@github.com:SEU-USUARIO/allpfit-analytics.git
cd allpfit-analytics
```

### 2. Configurar Ambiente

```bash
# Criar virtualenv
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configurar pre-commit hooks
pre-commit install
```

### 3. Criar Branch

```bash
# Sempre criar a partir de develop
git checkout develop
git pull origin develop
git checkout -b feature/minha-feature
```

**Nomenclatura de branches:**
- `feature/` - Novas funcionalidades
- `fix/` - Correções de bugs
- `docs/` - Documentação
- `refactor/` - Refatoração de código
- `test/` - Adição de testes

### 4. Fazer Mudanças

- Escreva código limpo e documentado
- Adicione testes para novas funcionalidades
- Mantenha compatibilidade com Python 3.11+
- Siga os padrões de código (ver abaixo)

### 5. Testar

```bash
# Rodar testes
pytest tests/ --verbose

# Verificar coverage
pytest tests/ --cov=src --cov-report=html

# Linting
black src tests
flake8 src tests
mypy src
```

### 6. Commit

```bash
# Commits devem seguir Conventional Commits
git add .
git commit -m "feat: adiciona análise de sentimento nas conversas"
```

**Tipos de commit:**
- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `docs:` Documentação
- `style:` Formatação (sem mudança de código)
- `refactor:` Refatoração
- `test:` Testes
- `chore:` Manutenção
- `perf:` Performance
- `ci:` CI/CD

**Exemplos:**
```
feat: adiciona integração com Slack para alertas
fix: corrige cálculo de taxa de conversão no dashboard
docs: atualiza README com instruções de deploy
refactor: reorganiza estrutura de pastas do ETL
test: adiciona testes para analyzer GPT-4
```

### 7. Push e PR

```bash
git push origin feature/minha-feature
```

Abra um Pull Request no GitHub:
- Use o template de PR
- Descreva as mudanças claramente
- Referencie issues relacionadas
- Aguarde review

## 🎨 Padrões de Código

### Python Style Guide

Seguimos [PEP 8](https://pep8.org/) com as seguintes configurações:

**Black (formatação):**
```bash
black --line-length 120 src tests
```

**Flake8 (linting):**
```bash
flake8 src tests --max-line-length=120 --ignore=E203,W503
```

**MyPy (type checking):**
```bash
mypy src --ignore-missing-imports
```

### Estrutura de Código

```python
"""
Module docstring explaining what this module does.

Example:
    from features.analyzers import rule_based
    analyzer = rule_based.RuleBasedAnalyzer()
"""

from typing import Dict, List, Optional
import pandas as pd


class MyClass:
    """Class docstring with description.

    Attributes:
        attribute_name: Description of attribute
    """

    def __init__(self, param: str) -> None:
        """Initialize MyClass.

        Args:
            param: Description of parameter
        """
        self.param = param

    def my_method(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Method docstring.

        Args:
            data: Input dataframe

        Returns:
            Dictionary with results

        Raises:
            ValueError: If data is empty
        """
        if data.empty:
            raise ValueError("Data cannot be empty")

        return {"result": "success"}
```

### Testes

- Use `pytest` para testes
- Organize em `tests/` espelhando estrutura de `src/`
- Nomeie arquivos como `test_*.py`
- Nomeie funções como `test_*`
- Use fixtures para dados de teste
- Aim for 80%+ coverage

**Exemplo:**
```python
# tests/test_analyzers.py
import pytest
from features.analyzers import rule_based


def test_analyze_conversation():
    """Test conversation analysis with valid data."""
    analyzer = rule_based.RuleBasedAnalyzer()
    result = analyzer.analyze({"id": 1, "messages": [...]})

    assert result["score"] >= 0
    assert result["score"] <= 10
    assert "suggestions" in result


@pytest.fixture
def sample_conversation():
    """Fixture providing sample conversation data."""
    return {
        "id": 1,
        "contact_name": "Test User",
        "messages": [...]
    }
```

## 🔄 Processo de Pull Request

### Antes de Submeter

- [ ] Código segue os padrões de estilo
- [ ] Testes passam localmente
- [ ] Coverage não diminuiu
- [ ] Documentação atualizada
- [ ] CHANGELOG.md atualizado (se aplicável)
- [ ] Commits seguem Conventional Commits

### Durante Review

- Responda aos comentários construtivamente
- Faça mudanças solicitadas em commits separados
- Não faça force push durante review
- Seja paciente e respeitoso

### Após Aprovação

- Squash commits se solicitado
- Aguarde merge pelo mantenedor

## 🐛 Reportando Bugs

Use o [template de issue](https://github.com/geniai-br/allpfit-analytics/issues/new?template=bug_report.md) e inclua:

- **Título claro:** "Bug: Descrição curta"
- **Versão:** Qual versão está usando
- **Passos para reproduzir:** Sequência exata
- **Comportamento esperado:** O que deveria acontecer
- **Comportamento atual:** O que acontece
- **Screenshots:** Se aplicável
- **Logs:** Erros relevantes
- **Ambiente:** OS, Python version, etc

## 💡 Sugerindo Features

Use o [template de feature request](https://github.com/geniai-br/allpfit-analytics/issues/new?template=feature_request.md) e inclua:

- **Título claro:** "Feature: Descrição curta"
- **Problema:** Qual problema resolve
- **Solução proposta:** Como funcionaria
- **Alternativas:** Outras abordagens consideradas
- **Contexto adicional:** Mockups, exemplos, etc

## 📞 Dúvidas?

- **Issues:** Para bugs e features
- **Discussions:** Para perguntas gerais
- **Email:** [seu-email@geniai.com]

---

**Obrigado por contribuir! 🎉**
