JURASSIC PARK 1993 FAN GAME — UE 5.8 STARTER BUILD
==================================================

WHAT THIS IS
A working C++ project scaffold for Unreal Engine 5.8, structured for a movie-sequence fan game.
No copyrighted movie footage, music, dialogue, logos, ripped models, or proprietary game assets are included.

CURRENT SYSTEMS
- First-person player base
- Enhanced Input hooks
- Line-trace interaction interface
- Objective component
- Mission trigger actor
- Automated spline-following tour vehicle pawn
- Dinosaur AI state base
- Film-route blockout coordinate data
- Eight-chapter/mission progression data
- Lumen/Nanite-ready project settings

FIRST OPEN
1. Install Unreal Engine 5.8.
2. Install Visual Studio 2022 with "Game development with C++" and the UE components.
3. Right-click JurassicPark1993.uproject -> Generate Visual Studio project files.
4. Build Development Editor / Win64.
5. Open the .uproject.

IMPORTANT
The Content/Maps/JP_Island_Blockout map cannot be authored as a binary .umap outside Unreal.
Create an Empty Open World map in the editor and save it exactly as:
    Content/Maps/JP_Island_Blockout

Then use Content/Data/JP1993_BlockoutRoute.json as the blockout reference.

RECOMMENDED FIRST BLUEPRINT ASSETS
Create:
- IA_Move (Axis2D)
- IA_Look (Axis2D)
- IA_Jump (Digital)
- IA_Interact (Digital)
- IMC_Player
- BP_JPPlayer derived from AJPPlayerCharacter
- BP_TourExplorer derived from AJPTourVehicle
- BP_DinosaurBase derived from AJPDinosaurAI

INPUT
WASD / left stick = Move
Mouse / right stick = Look
Space / controller face button = Jump
E / controller face button = Interact

MOVIE-ACCURATE DESIGN RULES FOR THIS PROJECT
- The waterfall/helipad is at the north-western end of the playable island blockout.
- The arrival drive passes through the large herbivore/Brachiosaurus valley before the Visitor Center.
- The automated tour begins at the Visitor Center/gates.
- The main tour route passes the Dilophosaurus area, then the sick Triceratops field, before the T. rex sequence.
- Jurassic tour gates belong on the tour departure route, not at the helicopter arrival.
- The project should reproduce the film's dramatic sequence without copying dialogue or redistributing copyrighted assets.

NEXT BUILD TARGET
Create the actual island graybox:
waterfall + helipad -> valley road -> Visitor Center -> raptor pen -> tour gates ->
Dilophosaurus paddock -> Triceratops field -> T. rex road and breakout arena.
