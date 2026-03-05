from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
STORYCHIEF_API_KEY = os.getenv("STORYCHIEF_API_KEY")

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/settings.html")
def settings():
    return send_from_directory(".", "settings.html")

@app.route("/generer", methods=["POST"])
def generer():
    data = request.json
    theme = data["theme"]
    consignes = data.get("consignes", "")
    structure = data.get("structure", "Introduction, 3 parties avec sous-titres, conclusion")
    ton = data.get("ton", "professionnel et informatif")
    style_image = data.get("style_image", "professional and modern, corporate style")
    marque = data.get("marque", "")
    date = data["date"]
    langue = data.get("langue", "fr")

    # Générer l'article + métadonnées
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": f"""Écris un article en {'français' if langue == 'fr' else 'anglais'} sur le thème : {theme}.

Structure : {structure}
Ton : {ton}
Consignes additionnelles : {consignes}
{f"Informations sur la marque à mentionner : {marque}" if marque else ""}

Formate le contenu en HTML avec des balises <h2>, <p>, <ul> etc. Sans balise <html> ou <body>.

Réponds UNIQUEMENT avec ce JSON (sans markdown) :
{{
  "content": "le contenu HTML de l'article",
  "excerpt": "un résumé de 2-3 phrases max",
  "seo_title": "un titre SEO optimisé de 60 caractères max",
  "seo_description": "une meta description de 155 caractères max"
}}"""
        }]
    )

    result = json.loads(response.choices[0].message.content)
    article = result["content"]
    excerpt = result["excerpt"]
    seo_title = result["seo_title"]
    seo_description = result["seo_description"]

    # Générer l'image
    image_response = client.images.generate(
        model="dall-e-3",
        prompt=f"Professional image for an article about: {theme}. Style: {style_image}",
        size="1792x1024"
    )
    image_url = image_response.data[0].url

    # Publier sur StoryChief immédiatement avec l'URL fraîche
    storychief_response = requests.post(
        "https://api.storychief.io/1.0/stories",
        headers={
            "Authorization": f"Bearer {STORYCHIEF_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        json={
            "title": theme,
            "content": article,
            "excerpt": excerpt,
            "seo_title": seo_title,
            "seo_description": seo_description,
            "language": langue,
            "featured_image": image_url,
            "due_at": date + "T09:00:00+00:00" if date else None
        }
    )


    print("StoryChief status:", storychief_response.status_code)
    print("StoryChief response:", storychief_response.text[:300])

    return jsonify({
        "article": article,
        "image_url": image_url,
        "storychief_status": storychief_response.status_code
    })

if __name__ == "__main__":
    app.run(debug=True)