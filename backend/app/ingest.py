from app.services.vector_store import seed_collection
if __name__=='__main__': print(f'Seeded {seed_collection()} products into Qdrant')
