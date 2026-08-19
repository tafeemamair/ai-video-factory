import json

def update_state(step, detail=""):
    with open("build_state.json", "w") as f:
        json.dump({
            "step": step,
            "detail": detail
        }, f)

def mark_scene_done(scene_id):
    import json
    with open("build_progress.json","w") as f:
        json.dump({
            "last_scene": scene_id
        }, f)

def get_last_scene():
    import os, json

    if not os.path.exists("build_progress.json"):
        return -1

    try:
        data = json.load(open("build_progress.json"))
        return data.get("last_scene", -1)
    except:
        return -1

