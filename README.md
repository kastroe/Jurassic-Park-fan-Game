Jurassic Park 1993 Fan Game
A fan-made Unreal Engine project inspired by the original Jurassic Park (1993) film.
The current goal is to recreate a playable Isla Nublar experience using the original film as the primary layout and visual reference, while also using recovered terrain data from the older Jurassic Dream CryEngine project as a terrain foundation and secondary reference.
> **Status:** Early development / environment and layout reconstruction  
> **Engine:** Unreal Engine 5.8 / 5.8.1  
> **Primary map in development:** `JP_JurassicDream_Terrain_Test`
---
Project Goals
The project is being built around a few core principles:
Recreate the feel and geography of Jurassic Park (1993) as closely as practical.
Use the film's park layout as the canonical source for important locations and the Tour Road.
Preserve the recovered Jurassic Dream terrain while adapting it to the film-inspired layout.
Build the park in safe, verifiable stages rather than making destructive map-wide edits.
Automate repetitive Unreal Editor work wherever possible using C++, Python, and OpenCode.
Keep important milestones under Git version control so risky changes can be rolled back safely.
---
Current Development State
Isla Nublar terrain
The project currently uses terrain recovered from the CryEngine-based Jurassic Dream project.
The source heightmap was decoded from CryEngine data and imported into Unreal as a Landscape.
Current Landscape configuration:
Resolution: 4081 × 4081
Components: 16 × 16
Section size: 255 × 255 quads
Water level: 50 m
Landscape actor: `JP_JurassicDream_Terrain`
The original CryEngine terrain and authored entities are treated as reference material rather than the final canonical park layout.
---
Jurassic Park 1993 Layout
The main layout is stored under:
```text
JP1993_Layout
```
Current canonical landmark markers include:
Visitor Center
Main Gate
Heliport
Port
T-Rex Paddock
Dilophosaurus
Brachiosaurus
Triceratops
Gallimimus
Velociraptor facility
These markers define the intended film-inspired macro layout.
The current landmark positions are considered fixed unless a deliberate layout redesign is made.
---
Tour Road
The approved Tour Road is based on the Jurassic Park tour concept from the 1993 film.
Current route:
```text
Visitor Center
→ Main Gate
→ Brachiosaurus
→ Gallimimus
→ Triceratops
→ T-Rex Paddock
→ Dilophosaurus
→ Visitor Center
```
The Heliport, Port, and Velociraptor facility are intentionally excluded from the public Tour Road.
Current Tour Road data
Spline actor: `TOUR_RoadGuide`
Control points: 14
Approximate length: 5.924 km
Maximum route slope: ~14.93°
Water crossings: 0
Self-intersections: 0
The route itself is now considered frozen.
Roadbed
A local Landscape grading pass has been completed beneath the approved Tour Road.
The grading pass:
modified only the local road corridor
used Unreal Landscape raw vertex editing
did not use render targets
did not use heightmap export/import rollback
preserved the approved spline
preserved all JP1993 landmark markers
preserved dry-land clearance
The Landscape under the Tour Road should now be treated as read-only unless a specific future terrain task is intentionally approved.
---
Road Visuals
The current road visual pass uses:
Asphalt width: 7.0 m
Center guide track width: 0.30 m
Guide track thickness: 0.04 m
The first visual version used many short flat mesh segments. These are being replaced with a smoother spline-deformed road system so the road follows the approved route and graded terrain without visible faceting or hard joins.
The centered guide track is intended to visually represent the automated Ford Explorer guidance system seen in the original film, rather than a conventional railway.
---
Important Maps
```text
Content/Maps/JP_JurassicDream_Terrain_Test.umap
```
Primary current development/test map.
```text
Content/Maps/JP_Island_Blockout.umap
```
Older production/blockout map.
```text
Content/Maps/JP_MovieMap_Landscape_Test.umap
```
Earlier illustrated movie-map terrain experiment.
The Jurassic Dream terrain test map is currently the main working environment for terrain, landmark, and Tour Road development.
---
Automation
The project makes extensive use of automation to avoid repetitive Unreal Editor work.
Unreal Python
Automation scripts live under:
```text
Scripts/
```
These scripts are used for tasks such as:
terrain import
landmark placement
marker generation
Tour Road creation
road verification
water checks
terrain grading
visual passes
map validation
Unreal C++
Project helper code lives under:
```text
Source/JurassicPark1993/
```
Notable helper libraries include:
```text
JPJurassicDreamLandscapeImportLibrary
JPWorldQueryLibrary
```
These provide native Unreal functionality where Python alone is unreliable or insufficient.
OpenCode
Project-level OpenCode configuration is stored under:
```text
.opencode/
```
OpenCode is used to assist with:
C++ implementation
Unreal Python automation
builds
scripted verification
source inspection
safe repeatable editor operations
Temporary OpenCode task history, caches, logs, sessions, and tests are excluded from Git.
---
Version Control
The project uses:
Git
GitHub
Git LFS
Repository:
```text
https://github.com/kastroe/Jurassic-Park-fan-Game
```
Large Unreal binary files such as:
```text
*.uasset
*.umap
*.fbx
*.glb
*.obj
*.r16
*.raw
```
are tracked through Git LFS where configured.
Generated Unreal folders such as the following are intentionally excluded:
```text
Binaries/
DerivedDataCache/
Intermediate/
Saved/
.vs/
```
Milestone workflow
Important or risky tasks should follow this pattern:
Check `git status`.
Commit and push a clean pre-change checkpoint.
Perform the task.
Verify the result in Unreal.
Confirm only intended files changed.
Commit and push the verified milestone.
Failed or partially broken states should not be committed as project milestones.
---
Safety Rules
This project has already encountered destructive Landscape failure during experimentation, so several rules are now mandatory.
Do not use
render-target Landscape rollback
heightmap export/import as an emergency rollback mechanism
broad destructive Landscape edits without a verified backup
untested changes directly on the production map
Before risky changes
use the test map or a disposable duplicate
create a Git checkpoint
verify the exact files being modified
preserve the frozen Tour Road spline and JP1993 landmark markers unless the task explicitly requires changing them
---
Reference Assets
The project currently contains third-party reference/model assets including:
Visitor Center
Located under:
```text
Reference/VisitorCenter/
```
Creator: reeee  
License: CC BY 4.0
Jurassic Park Gate
Located under:
```text
Reference/Gate/
```
Creator: Mat Jolicoeur  
License: CC BY 4.0
Additional attribution details are maintained in:
```text
THIRD_PARTY_ATTRIBUTION.md
```
---
Project Structure
A simplified overview:
```text
JurassicPark1993_FanGame_UE58/
├── Config/
├── Content/
│   ├── Data/
│   ├── JPBlockout/
│   ├── JPGenerated/
│   ├── JPImported/
│   ├── Maps/
│   ├── Temp/
│   └── __ExternalActors__/
├── Reference/
│   ├── Gate/
│   ├── IslandBaseModel/
│   ├── JurassicDreamTerrain/
│   ├── MovieMapLandscape/
│   └── VisitorCenter/
├── Scripts/
├── Source/
│   └── JurassicPark1993/
├── .opencode/
├── JurassicPark1993.uproject
├── THIRD_PARTY_ATTRIBUTION.md
└── README.md
```
---
Build
The project is currently developed with Unreal Engine 5.8.x on Windows.
Typical editor build:
```powershell
& "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" `
  JurassicPark1993Editor Win64 Development `
  -project="C:\Users\KASTROE\Downloads\JurassicPark1993_FanGame_UE58\JurassicPark1993.uproject" `
  -WaitMutex
```
Local paths will naturally differ on other machines.
---
Disclaimer
This is an unofficial, non-commercial fan project.
Jurassic Park, its characters, locations, names, logos, and related intellectual property belong to their respective rights holders.
This project is not affiliated with, endorsed by, sponsored by, or associated with Universal Pictures, Amblin Entertainment, Steven Spielberg, CrichtonSun LLC, or any other official Jurassic Park rights holder.
Third-party assets remain subject to their own licenses and attribution requirements.
---
Development Philosophy
The project is intentionally being built in controlled milestones.
Once a major element is approved — such as the island orientation, park landmark layout, Tour Road route, or graded roadbed — it is frozen so later work improves the next layer rather than repeatedly breaking previously approved work.
The immediate development focus is turning the approved blockout into a believable, smooth, drivable recreation of the Jurassic Park tour environment.
