import unreal
import json
import os

project_dir = unreal.Paths.project_dir()
json_path = os.path.join(project_dir, "Content", "JPBlockout", "JP1993_Landmarks.json")

with open(json_path, "r", encoding="utf-8") as f:
    landmarks = json.load(f)

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# Remove any markers created by an older version of the script.
for actor in actor_sub.get_all_level_actors():
    if actor.get_actor_label().startswith("AUTO_JP_"):
        actor_sub.destroy_actor(actor)

# Put the markers well above the graybox terrain so they are easy to find.
marker_z = 45000.0

for lm in landmarks:
    loc = unreal.Vector(float(lm["world_x_cm"]), float(lm["world_y_cm"]), marker_z)
    actor = actor_sub.spawn_actor_from_class(unreal.TargetPoint, loc, unreal.Rotator())
    actor.set_actor_label("AUTO_JP_" + lm["name"])

unreal.EditorLevelLibrary.save_current_level()
unreal.log("JP Build 0.2.1: Corrected landmark markers created and level saved.")
