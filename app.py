from flask import Flask, render_template, request, session
import ollama

app = Flask(__name__)

# Used to store the current user's recommendation data
app.secret_key = "exp4-personalized-recommendation"


# ============================================================
# HELPER FUNCTION - DETECT USER INTENT LOCALLY
# ============================================================

def detect_intent(feedback):
    """
    Detect the user's intent without calling the LLM.
    This makes the feedback process faster.
    """

    text = feedback.lower()

    intents = []
    details = []

    # Topic preference
    topic_words = [
        "python",
        "sql",
        "machine learning",
        "data analytics",
        "data science",
        "power bi",
        "javascript",
        "react",
        "cloud",
        "docker",
        "kubernetes"
    ]

    found_topics = [
        topic for topic in topic_words
        if topic in text
    ]

    if found_topics:
        intents.append("topic_preference")
        details.append(
            "The user prefers topics related to "
            + ", ".join(found_topics)
        )

    # Skill level
    if any(word in text for word in [
        "beginner",
        "basic",
        "basics",
        "easy"
    ]):
        intents.append("skill_level_preference")
        details.append("The user prefers beginner-friendly content.")

    elif any(word in text for word in [
        "advanced",
        "expert",
        "complex"
    ]):
        intents.append("skill_level_preference")
        details.append("The user prefers advanced-level content.")

    elif "intermediate" in text:
        intents.append("skill_level_preference")
        details.append("The user prefers intermediate-level content.")

    # Learning style
    if any(word in text for word in [
        "practical",
        "project",
        "hands-on",
        "hands on",
        "practice"
    ]):
        intents.append("learning_style")
        details.append(
            "The user prefers practical or project-based learning."
        )

    if any(word in text for word in [
        "theory",
        "theoretical"
    ]):
        intents.append("learning_style")
        details.append(
            "The user has expressed a preference regarding theoretical content."
        )

    # Budget
    if any(word in text for word in [
        "free",
        "cheap",
        "affordable",
        "budget",
        "low cost",
        "no cost"
    ]):
        intents.append("budget_preference")
        details.append(
            "The user prefers free or affordable resources."
        )

    # Category
    if any(word in text for word in [
        "course",
        "courses"
    ]):
        intents.append("category_preference")
        details.append("The user prefers courses.")

    if any(word in text for word in [
        "book",
        "books"
    ]):
        intents.append("category_preference")
        details.append("The user prefers books.")

    if any(word in text for word in [
        "project",
        "projects"
    ]):
        intents.append("category_preference")
        details.append("The user prefers projects.")

    # Difficulty
    if any(word in text for word in [
        "easy",
        "simple"
    ]):
        intents.append("difficulty_preference")
        details.append("The user prefers easier recommendations.")

    if any(word in text for word in [
        "challenging",
        "difficult"
    ]):
        intents.append("difficulty_preference")
        details.append(
            "The user prefers challenging recommendations."
        )

    # General refinement
    if not intents:
        intents.append("general_refinement")
        details.append(
            "The user wants the recommendations refined according to the provided feedback."
        )

    # Remove duplicate intents
    intents = list(dict.fromkeys(intents))

    detected_intent = (
        "Intent: " + ", ".join(intents)
        + "\n\nDetails: "
        + " ".join(details)
    )

    return detected_intent


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


# ============================================================
# GENERATE INITIAL RECOMMENDATIONS
# ============================================================

@app.route("/recommend", methods=["POST"])
def recommend():

    # Collect user profile information
    profile = {
        "name": request.form.get("name", ""),
        "age": request.form.get("age", ""),
        "background": request.form.get("background", ""),
        "interests": request.form.get("interests", ""),
        "skill_level": request.form.get("skill_level", "Beginner"),
        "category": request.form.get("category", ""),
        "goal": request.form.get("goal", ""),
        "preferences": request.form.get("preferences", ""),
        "number": request.form.get("number", "5")
    }

    # --------------------------------------------------------
    # Optimized prompt
    # --------------------------------------------------------

    prompt = f"""
You are a personalized recommendation assistant.

USER PROFILE:
Name: {profile["name"]}
Age: {profile["age"]}
Background: {profile["background"]}
Interests: {profile["interests"]}
Skill Level: {profile["skill_level"]}
Category: {profile["category"]}
Goal: {profile["goal"]}
Preferences: {profile["preferences"]}

Generate exactly {profile["number"]} relevant recommendations.

Rules:
- Use only the information provided.
- Match the user's interests, goal, skill level and preferences.
- Do not invent personal information.
- Rank from highest to lowest suitability.
- Give a score from 0-100.
- Give a short explanation.
- Avoid unrelated recommendations.
- Keep explanations concise.

Format:

Recommendation 1:
Name:
Suitability Score:
Explanation:

Recommendation 2:
Name:
Suitability Score:
Explanation:

Continue until exactly {profile["number"]} recommendations are provided.
"""

    # --------------------------------------------------------
    # Ollama
    # --------------------------------------------------------

    response = ollama.chat(
        model="llama3.2",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        options={
            "temperature": 0.3,
            "num_predict": 700
        },
        keep_alive=-1
    )

    recommendations = response["message"]["content"]

    # --------------------------------------------------------
    # Save profile and recommendations
    # --------------------------------------------------------

    session["profile"] = profile
    session["recommendations"] = recommendations

    # Send profile back to HTML so inputs remain visible
    return render_template(
        "index.html",
        recommendations=recommendations,
        profile=profile
    )


# ============================================================
# FEEDBACK + INTENT + REFINED RECOMMENDATIONS
# ============================================================

@app.route("/feedback", methods=["POST"])
def feedback():

    # Get feedback
    feedback_text = request.form.get("feedback", "").strip()

    # Retrieve previous data
    profile = session.get("profile")
    previous_recommendations = session.get("recommendations")

    # Check whether recommendations exist
    if not profile or not previous_recommendations:

        return render_template(
            "index.html",
            error="Please generate recommendations before submitting feedback."
        )

    # --------------------------------------------------------
    # Detect intent locally
    # --------------------------------------------------------

    detected_intent = detect_intent(feedback_text)

    # --------------------------------------------------------
    # Refinement prompt
    # --------------------------------------------------------

    refinement_prompt = f"""
You are a personalized recommendation assistant.

USER PROFILE:
Name: {profile["name"]}
Age: {profile["age"]}
Background: {profile["background"]}
Interests: {profile["interests"]}
Skill Level: {profile["skill_level"]}
Category: {profile["category"]}
Goal: {profile["goal"]}
Preferences: {profile["preferences"]}

PREVIOUS RECOMMENDATIONS:
{previous_recommendations}

USER FEEDBACK:
{feedback_text}

DETECTED INTENT:
{detected_intent}

Generate exactly {profile["number"]} improved recommendations.

Rules:
- Respect the original profile.
- Follow the user's feedback.
- Use the detected intent.
- Replace recommendations that do not match the feedback.
- Rank from highest to lowest suitability.
- Give a score from 0-100.
- Give a short explanation.
- Avoid unrelated recommendations.
- Keep explanations concise.

Format:

Refined Recommendation 1:
Name:
Suitability Score:
Explanation:

Refined Recommendation 2:
Name:
Suitability Score:
Explanation:

Continue until exactly {profile["number"]} recommendations are provided.
"""

    # --------------------------------------------------------
    # Ask Ollama for refined recommendations
    # --------------------------------------------------------

    response = ollama.chat(
        model="llama3.2",
        messages=[
            {
                "role": "user",
                "content": refinement_prompt
            }
        ],
        options={
            "temperature": 0.3,
            "num_predict": 700
        },
        keep_alive=-1
    )

    refined_recommendations = response["message"]["content"]

    # Update recommendations
    session["recommendations"] = refined_recommendations

    # Keep the profile visible
    return render_template(
        "index.html",
        recommendations=refined_recommendations,
        detected_intent=detected_intent,
        feedback_submitted=True,
        profile=profile
    )


# ============================================================
# RUN FLASK APPLICATION
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)