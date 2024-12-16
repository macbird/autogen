from src.tools.tools import get_database_structure, criar_template_html_protocolo, send_email, gerar_numero_protocolo, \
    cancelar_assinatura_api, buscar_assinaturas_ativas, buscar_assinaturas_ativas_api

# # Exemplo de uso
# resultado = get_database_structure()
# print(resultado)

response = buscar_assinaturas_ativas_api("111.222.333-44")
print(response)