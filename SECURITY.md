# 🔒 Política de Segurança

## Versões Suportadas

| Versão | Suportada          |
| ------ | ------------------ |
| 1.2.x  | ✅ Sim             |
| 1.0.x  | ✅ Sim             |
| < 1.0  | ❌ Não             |

## 🐛 Reportando Vulnerabilidades

A segurança é nossa prioridade. Se você descobrir uma vulnerabilidade de segurança, **NÃO** abra uma issue pública.

### Processo de Reporte

1. **Email:** Envie detalhes para `security@geniai.com` (ou contato apropriado)
2. **Assunto:** `[SECURITY] Descrição curta da vulnerabilidade`
3. **Inclua:**
   - Descrição detalhada da vulnerabilidade
   - Passos para reproduzir
   - Impacto potencial
   - Versão afetada
   - Sugestão de correção (se houver)

### O que esperar

- **Confirmação:** Dentro de 48 horas
- **Avaliação:** Análise completa em 7 dias
- **Correção:** Patch em 30 dias para vulnerabilidades críticas
- **Divulgação:** Coordenada após correção

### Recompensas

Agradecemos pesquisadores que reportam vulnerabilidades responsavelmente:
- Menção nos créditos (se desejar)
- Reconhecimento no CHANGELOG
- Possível recompensa monetária (a definir)

## 🛡️ Práticas de Segurança

### Credenciais

- ✅ **NUNCA** commite credenciais no código
- ✅ Use `.env` para variáveis sensíveis
- ✅ `.env` está no `.gitignore`
- ✅ Use `.env.example` como template sem dados reais

### Banco de Dados

- ✅ Usuário read-only no banco remoto
- ✅ Banco local isolado
- ✅ Conexões via SSL/TLS quando disponível
- ✅ Senhas com hash (se aplicável)

### Código

- ✅ Validação de entrada
- ✅ Sanitização de queries SQL (SQLAlchemy)
- ✅ Não expor informações sensíveis em logs
- ✅ Scan de segurança via Bandit (CI/CD)

### Dependências

- ✅ Dependabot habilitado
- ✅ Revisar atualizações de segurança
- ✅ Manter dependências atualizadas
- ✅ `pip-audit` para auditar pacotes

### Deploy

- ✅ HTTPS obrigatório em produção
- ✅ Firewall configurado
- ✅ Acesso restrito ao servidor
- ✅ Logs protegidos

## 🔍 Auditoria de Segurança

### Checklist Mensal

- [ ] Revisar dependências vulneráveis
- [ ] Atualizar pacotes desatualizados
- [ ] Verificar logs de segurança
- [ ] Revisar permissões de acesso
- [ ] Testar backup e recuperação

### Ferramentas

```bash
# Scan de vulnerabilidades em dependências
pip install pip-audit
pip-audit

# Scan de código com Bandit
pip install bandit
bandit -r src

# Verificar secrets no código
pip install detect-secrets
detect-secrets scan
```

## 📋 Vulnerabilidades Conhecidas

### v1.2 (Atual)
- Nenhuma vulnerabilidade conhecida

### v1.0
- Credenciais hardcoded em `crossmatch_excel_crm.py` - **CORRIGIDO em v1.2**

## 🔐 Contatos de Segurança

- **Email:** security@geniai.com
- **PGP Key:** [Link para chave pública se houver]
- **Tempo de Resposta:** 48 horas (dias úteis)

## 📚 Recursos

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)

---

**Última atualização:** Outubro 2025
