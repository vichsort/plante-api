from celery.schedules import crontab

# Um problema com esse worker: Celery é síncrono por natureza mas o 
# repositório é async. O asyncio.run() funciona mas é feio. Quando for 
# implementar o adapter concreto do repositório, podemos considerar uso uso
# de celery-pool-asyncio ou criar uma versão síncrona do método 
# get_confirmed_before só para o worker.

beat_schedule = {
    "anonymize-confirmed-samples-daily": {
        "task": "workers.anonymize_confirmed_samples",
        "schedule": crontab(hour=3, minute=0),  # toda madrugada às 03h00 UTC
    },
}