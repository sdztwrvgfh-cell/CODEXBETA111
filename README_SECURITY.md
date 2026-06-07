Segurança da API Key (OpenAI)

1) REVOGAR a chave vazada agora (faça no painel da OpenAI):
   - https://platform.openai.com/account/api-keys
   - Revoke/Delete a chave que foi exposta.

2) GERAR nova chave no painel da OpenAI.

3) CONFIGURAR localmente (duas opções):

   a) Usar variáveis de ambiente (temporário para sessão atual):

   PowerShell (apenas sessão atual):
   ```powershell
   $env:OPENAI_API_KEY = "SUA_NOVA_CHAVE"
   ```

   PowerShell (persistente - reinicie o terminal depois):
   ```powershell
   setx OPENAI_API_KEY "SUA_NOVA_CHAVE"
   ```

   Bash (Linux / macOS):
   ```bash
   export OPENAI_API_KEY="SUA_NOVA_CHAVE"
   ```

   b) Usar `st.secrets` do Streamlit (recomendado para desenvolvimento local):
   - Crie um arquivo `.streamlit/secrets.toml` (não commitar):
   ```toml
   OPENAI_API_KEY = "SUA_NOVA_CHAVE"
   ```
   - O repositório já contém `.streamlit/secrets.toml.example` como modelo. Certifique-se de que `.streamlit/` está em `.gitignore`.

4) TESTAR
   - Reinicie o app Streamlit e envie uma mensagem para verificar se o Codex responde.

5) BOAS PRÁTICAS
   - Nunca cole a chave em chats públicos, issues, ou commits.
   - Se uma chave vazar, revogue-a imediatamente e gere outra.
   - Use quotas e alertas na conta da OpenAI.

Se quiser, eu posso (opcional):
- remover automaticamente strings que começam com `sk-` (procuro e substituo) — útil se você tiver copiado a chave em algum arquivo;
- ajudar a configurar `.streamlit/secrets.toml` no seu sistema local.
