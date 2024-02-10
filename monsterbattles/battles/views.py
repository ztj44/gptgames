from django.shortcuts import render, redirect
from .models import Monster

from openai import OpenAI
from django.conf import settings
import json
from random import randint
import requests
from django.core.files.base import ContentFile

client = OpenAI()


def home(request):
    return render(request, "home.html")


def submit_character_prompt(request):
    if request.method == "POST":
        prompt = request.POST.get("prompt")
        # Generate character details
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant designed to output JSON. Generate a character with a name, description, an attack_1, an attack_1_description, an attack_2, an attack_2_description, an attack_3, an attack_3_description, a strength, and a weakness.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        print("response: " + response.choices[0].message.content)

        character_details = response.choices[0].message.content
        if isinstance(character_details, str):
            character_details = json.loads(character_details)
        else:
            # TODO validate the json output and iterate maybe?
            print("Error parsing json")

        # Redirect to the character review page, passing the generated details (Consider using session or cache based on your preference)
        request.session["character_details"] = character_details
        return redirect("review_character")
    else:
        return render(request, "submit_prompt.html")


def review_character(request):
    character_details = request.session.get("character_details")
    if not character_details:
        return redirect(
            "submit_character_prompt"
        )  # Redirect if there's no character data

    # If character_details is a string, parse it back to a dictionary
    if isinstance(character_details, str):
        character_details = json.loads(character_details)
    else:
        # TODO error handling
        print("Json parse issue")

    # Generate an image for the character
    image_response = client.images.generate(
        model="dall-e-3",
        prompt=character_details["description"],
        size="1024x1024",
        n=1,
    )

    image_url = image_response.data[0].url
    # Download the image
    response = requests.get(image_url)
    if response.status_code == 200:
        # Assuming you have MEDIA_ROOT set up in your settings and a path for these images
        image_path = (
            f"monster_images/{character_details['name'].replace(' ', '_').lower()}.png"
        )
        full_path = f"{settings.MEDIA_ROOT}/{image_path}"

        # Save the image locally
        with open(full_path, "wb") as f:
            f.write(response.content)

    else:
        print("Error from open ai ", response)

    if request.method == "POST":
        if "accept" in request.POST:
            # Save the character to the database
            Monster.objects.create(
                name=character_details["name"],
                description=character_details["description"],
                attack_1=character_details["attack_1"],
                attack_1_description=character_details["attack_1_description"],
                attack_2=character_details["attack_2"],
                attack_2_description=character_details["attack_2_description"],
                attack_3=character_details["attack_3"],
                attack_3_description=character_details["attack_3_description"],
                strength=character_details["strength"],
                weakness=character_details["weakness"],
                image_url=image_url,
            )
            return redirect(
                "home"
            )  # Redirect to a page where all characters are listed
        else:
            return redirect(
                "submit_character_prompt"
            )  # If the user chooses to regenerate

    context = {
        "character_details": character_details,
        "image_url": image_url,
    }
    return render(request, "review_character.html", context)


def choose_monsters(request):
    if request.method == "POST":
        # IDs of selected monsters will be sent from the form
        monster1_id = request.POST.get("monster1")
        monster2_id = request.POST.get("monster2")
        request.session["arena"] = {"monster1": monster1_id, "monster2": monster2_id}
        return redirect("arena")
    else:
        monsters = Monster.objects.all()
        return render(request, "choose_monsters.html", {"monsters": monsters})


def arena(request):
    # Initialize or update the game state
    if "arena_state" not in request.session:
        request.session["arena_state"] = {
            "turn": 1,  # Start with monster 1's turn
            "monster1_health": 100,
            "monster2_health": 100,
            "last_attack_description": "",
            "last_attack_image_url": "",
        }

    # Retrieve monsters and arena state from session
    arena_state = request.session["arena_state"]
    monster1_id = request.session.get("arena", {}).get("monster1")
    monster2_id = request.session.get("arena", {}).get("monster2")

    try:
        monster1 = Monster.objects.get(id=monster1_id)
        monster2 = Monster.objects.get(id=monster2_id)
    except Monster.DoesNotExist:
        # Redirect if any monster does not exist
        return redirect("choose_monsters")

    # Process attack
    if request.method == "POST":
        attacker = monster1 if arena_state["turn"] == 1 else monster2
        defender = monster2 if arena_state["turn"] == 1 else monster1
        # Assume attacker and defender are already defined as either monster1 or monster2 based on the turn
        attacker_attack = request.POST.get("attack")  # Example: 'attack_1'
        attack_name = getattr(attacker, attacker_attack)  # Example: attacker.attack_1
        attack_description = getattr(
            attacker, attacker_attack + "_description"
        )  # Example: attacker.attack_1_description

        # Construct a detailed description for the OpenAI prompt
        user_content = f"""
        {attacker.name}, is a monster with a description {attacker.description} with its strength of {attacker.strength} and weakness of {attacker.weakness}, launches an attack called {attack_name} ({attack_description}) against {defender.name} with a description with a description {defender.description}, known for its strength of {defender.strength} and weakness of {defender.weakness}.
        """
        print("User attack string ", user_content)

        # Generate attack outcome description using OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a video game engine designed to output JSON with two keys damage(must be an integer between 1 and 75) and description(describes what happened). Based on the information provided by the user, describe the outcome of the attack including any damage. TO DETERMINE HOW EFFECTIVE IT IS CONSIDER THE STRENGTHS AND WEAKNESSES OF BOTH THE ATTACKER AND DEFENDER. A VERY EFFECTIVE ATTACK SHOULD BE 60-75 A NOT VERY EFFECTIVE ATTACK SHOULD BE BELOW 15. IT SHOULD BE SOMEWHAT RANDOM THOUGH",
                },
                {"role": "user", "content": user_content},
            ],
        )

        # Parse the response and update the game state
        attack_result = json.loads(response.choices[0].message.content)
        print("Attack result:", attack_result)
        damage = attack_result["damage"]
        description = attack_result["description"]

        # Update health
        if arena_state["turn"] == 1:
            arena_state["monster2_health"] -= damage
        else:
            arena_state["monster1_health"] -= damage

        # Check for game over
        if arena_state["monster1_health"] <= 0 or arena_state["monster2_health"] <= 0:
            winner_id = (
                monster1_id if arena_state["monster1_health"] > 0 else monster2_id
            )
            loser_id = monster2_id if winner_id == monster1_id else monster1_id
            return redirect("defeat_page", winner_id=winner_id, loser_id=loser_id)
        # Generate image for the attack
        # image_response = client.images.generate(
        #     model="dall-e-3",
        #     prompt=f"You are going to draw the outcome of a video game battle between the attacker: {attacker.description} and the defender: {defender.description}. The first monster attacked the second and the outcome was: {description} in a fantasy battle.",
        #     size="1024x1024",
        #     n=1,
        # )
        # image_url = image_response.data[0].url

        # Update arena state
        arena_state["last_attack_description"] = description
        # arena_state["last_attack_image_url"] = image_url
        arena_state["turn"] = 2 if arena_state["turn"] == 1 else 1  # Switch turns

        request.session["arena_state"] = arena_state

    context = {
        "monster1": monster1,
        "monster2": monster2,
        "arena_state": arena_state,
    }

    return render(request, "arena.html", context)


def defeat(request, winner_id, loser_id):
    if "arena_state" in request.session:
        del request.session["arena_state"]
    try:
        winner = Monster.objects.get(id=winner_id)
        loser = Monster.objects.get(id=loser_id)
    except Monster.DoesNotExist:
        # Redirect or show an error if the monsters aren't found
        return render(request, "error_page.html", {"message": "Monster not found."})

    context = {
        "winner": winner,
        "loser": loser,
    }
    return render(request, "defeat.html", context)
