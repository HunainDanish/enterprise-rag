from app.rag.vectorstore import get_collection, delete_document

DOCUMENT_ID = "d70c01ad-eff9-417e-bdcf-a920f6ec7470"  # Replace with a real document ID

collection = get_collection()

before = collection.count()
print(f"Before delete: {before}")

delete_document(DOCUMENT_ID)

after = collection.count()
print(f"After delete: {after}")