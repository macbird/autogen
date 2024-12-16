import asyncio


async def retry_async(operation, max_retries=2, delay=2):
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            print(f"Tentativa {attempt + 1}/{max_retries}: falhou. {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
    raise Exception("Falha ao executar operação após várias tentativas.")