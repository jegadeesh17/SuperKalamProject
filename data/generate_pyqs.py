import json
import uuid

def main():
    path = "data/seed_data.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    new_pyqs = []
    
    topics = [t["id"] for t in data["topics"]]
    
    for i in range(1, 21):
        topic_id = topics[i % len(topics)]
        pyq = {
            "id": f"mock-pyq-{i}-{uuid.uuid4().hex[:6]}",
            "topic_id": topic_id,
            "question_text": f"Discuss the significance of the topic '{topic_id}' in the context of recent developments in India. (Mock Question {i})",
            "year": 2024,
            "word_limit": 250,
            "difficulty": "moderate",
            "model_answer": f"This is a mock model answer for {topic_id}. It covers all aspects including the constitutional provisions, historical background, and contemporary relevance. The government has taken several steps to address the challenges, but structural issues remain. A multi-pronged approach is needed.",
            "key_points": [
                "Constitutional background",
                "Recent developments",
                "Government initiatives",
                "Challenges and way forward"
            ]
        }
        new_pyqs.append(pyq)
        
    if "pyqs" not in data:
        data["pyqs"] = []
        
    data["pyqs"].extend(new_pyqs)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        
    print(f"Added {len(new_pyqs)} mock PYQs. Total PYQs now: {len(data['pyqs'])}")

if __name__ == "__main__":
    main()
