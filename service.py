import pymongo

client = pymongo.MongoClient('mongodb://192.168.56.1:27017/')
db = client['licenta']
collection = db['zones']

print("Asd")

for doc in collection.find():
    print(doc)
