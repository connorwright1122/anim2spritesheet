# anim2spritesheet
 
A Blender addon to automate the creation of pixel art spritesheets from 3D models inspired by the process used by Motion Twin for Dead Cells. 
This also provides the ability to render normal map spritesheets for dynamic lighting of sprites in game engines. 

## How to Use
1. Install add-on
2. In Blender scene hierarchy, set primary camera that focuses on animation
3. Enter anim2spritesheet n-panel in Render tab (hit N, navigate to Render > anim2spritesheet) 
4. Set resolution and start/end frames of animation
5. Select checkboxes based on what renders you want (base, normal)
6. Choose output directory (will create subfolders based on checkboxes that overwrite previous)
7. Hit Render button

## Tips
* Rendering will create 2 subfolders in the selected output directory (Base, Normal) with all the rendered frames. This will overwrite previous Base/Normal folders in the output directory, so you should create a new directory for every individual sprite. Spritesheets are put in the top level of the selected directory. 
* Not tested on Linux 

## Resources
https://github.com/CGArtPython/blender_plus_python/blob/main/add-ons/simple_custom_panel/simple_custom_panel.py
https://github.com/luckychris/install_blender_python_modules/tree/main
https://python-pillow.org/
https://docs.blender.org/api/current/index.html
