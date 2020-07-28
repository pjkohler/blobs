import bpy
import math
import random 
import numpy as np
import mathutils
import os
import matplotlib.pyplot as plt

def update_camera(camera, focus_point=mathutils.Vector((0.0, 0.0, 0.0)), distance=10.0):
    """
    Focus the camera to a focus point and place the camera at a specific distance from that
    focus point. The camera stays in a direct line with the focus point.

    :param camera: the camera object
    :type camera: bpy.types.object
    :param focus_point: the point to focus on (default=``mathutils.Vector((0.0, 0.0, 0.0))``)
    :type focus_point: mathutils.Vector
    :param distance: the distance to keep to the focus point (default=``10.0``)
    :type distance: float
    """
    looking_direction = camera.location - focus_point
    rot_quat = looking_direction.to_track_quat('Z', 'Y')
    camera.rotation_euler = rot_quat.to_euler()
    camera.location = rot_quat @ mathutils.Vector((0.0, 0.0, distance))

def add_mball(type='BALL', radius=0.2, location=(0,0,0), rotation=(0,0,0)):
    bpy.ops.object.metaball_add(type=type, radius=radius, enter_editmode=False, location=location, rotation=rotation)
    bpy.context.object.data.resolution = 0.05
    bpy.context.object.data.render_resolution = 0.05
    bpy.context.object.data.threshold = 0.5

def sphere_pts(n_pts, n_smp, radius, min_dist, previous):
    # equally sampled points on either side of the y-axis
    # if x = 0 for previous data point, generate equal number of points on either side of x-axis
    assert np.mod(n_pts, 2) == 0, "number of points must be equal"
    theta =(math.pi)/n_smp
    phi = (2*math.pi)/n_smp

    vertices = []
    for stack in range(n_smp):
        stackRadius = math.sin(theta*stack) * radius
        for slice in range(n_smp):
            x = math.cos(phi*slice) * stackRadius
            y = math.sin(phi*slice) * stackRadius
            z = math.cos(theta*stack) * radius
            vertices.append([x,y,z])
    random.shuffle(vertices) # randomize vertices
    if previous[0] < 0: 
        vertices  = [a for a in vertices if a[0]+previous[0] < 0]
    elif previous[0] > 0:
        vertices  = [a for a in vertices if a[0]+previous[0] > 0]
    if previous[0] == 0:
        left_v  = [a for a in vertices if a[0] < -min_dist]
        right_v = [a for a in vertices if a[0] > min_dist]
        assert len(left_v) == len(right_v), "there must be same number of left and right vertices"
        left_o = left_v[0:np.int(n_pts/2)]
        right_o = right_v[0:np.int(n_pts/2)]
        locations = left_o + right_o
    else:
        locations = vertices[0:n_pts]
    return locations

def symmetrize(loc):
    l_pts = [a for a in loc if a[0] < 0]
    r_pts = []
    for i in range(len(l_pts)):
        r_pts.append([l_pts[i][0]*-1, l_pts[i][1], l_pts[i][2], l_pts[i][3]])
    out = l_pts + r_pts
    assert len(out) == len(loc), "output must be same length as input"
    return out

# object making function
def make_objects(asymmetric=False, min_dist=0.05, save_images=True, bg_color=(.05, .05, .05), ob_color=(1, 1, 1, 1), out_dir=None):        
        # parameters below are quite arbitrary and should not be changed
        num_smp = 20
        meta_n = (8, 4, 2)
        meta_r = (.6, .4, .2)
        meta_d = (1.2, .8, .4)
        meta_coords = []
        loc_pts = [[0,0,0]]
        for i in range(len(meta_n)):
            cur_loc_pts = loc_pts
            for q in range(len(loc_pts)):
                loc_tmp = sphere_pts(meta_n[i], num_smp, meta_d[i], min_dist, loc_pts[q])
                loc_tmp = [ [a+loc_pts[q][0], b+loc_pts[q][1], c+loc_pts[q][2], meta_r[i]] for (a, b, c) in loc_tmp ]
                loc_pts = loc_pts + [ x[0:3] for x in loc_tmp ]
                meta_coords = meta_coords + loc_tmp
            for d in cur_loc_pts: loc_pts.remove(d)
        if not asymmetric:
            meta_coords = symmetrize(meta_coords)

        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.select_by_type(type='META')
        bpy.ops.object.delete(use_global=False)
        bpy.ops.object.select_by_type(type='MESH')
        bpy.ops.object.delete(use_global=False)
        bpy.ops.object.select_by_type(type='CAMERA')
        bpy.ops.object.delete(use_global=False)
        bpy.ops.object.select_by_type(type='LIGHT')
        bpy.ops.object.delete(use_global=False)

        # add two lights
        bpy.ops.object.light_add(type='POINT', location=(0, -10, 10))
        bpy.context.object.data.energy = 5000
        bpy.context.object.data.shadow_soft_size = 5
        bpy.ops.object.light_add(type='POINT', location=(0, 15, 0))
        bpy.context.object.data.energy = 50000
        bpy.context.object.data.shadow_soft_size = 5

        # add two cameras
        bpy.ops.object.camera_add(enter_editmode=False, align='WORLD', location=(0, -6, 3), rotation=(0, 0, 0))
        bpy.ops.object.camera_add(enter_editmode=False, align='WORLD', location=(2, -4, 3), rotation=(0, 0, 0))

        #add_mball(type="BALL", radius=.25, location=[0,0,0])

        for i in range(len(meta_coords)):
            coordinate = (meta_coords[i][0], meta_coords[i][1], meta_coords[i][2])
            add_mball(type="BALL", radius=meta_coords[i][3], location=coordinate)

        # convert to mesh
        bpy.ops.object.convert(target='MESH')

        # set background color to dark gray
        bpy.context.scene.world.color = bg_color

        act = bpy.context.active_object # set active object to variable

        mat_name = "meta_mat"
        # Test if material exists
        # If it does not exist, create it:
        mat = (bpy.data.materials.get(mat_name) or 
                bpy.data.materials.new(mat_name))
        mat = bpy.data.materials[mat_name]
        act.data.materials.append(mat) #add the material to the object
        bpy.context.object.active_material.diffuse_color = ob_color #change color
        bpy.context.object.active_material.metallic = 0.1

        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
        bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='MEDIAN')

        path_dir = out_dir #save for restore

        for z in range(2):
            if z == 0:
                suffix = 'a'
                rotated = False
            else:
                suffix = 'b'
                rotated = True
                bpy.ops.transform.rotate(value=3.14159, orient_axis='Z', orient_type='GLOBAL')
            
            for c, cam in enumerate([obj for obj in bpy.data.objects if obj.type == 'CAMERA']):
                # position the camera
                update_camera(cam)
                bpy.context.scene.camera = cam
                # image settings 
                bpy.context.scene.render.image_settings.color_depth = '16'
                bpy.context.scene.render.image_settings.compression = 25
                # rendering settings (should be tested more extensively)
                bpy.context.scene.render.pixel_aspect_x = 1
                bpy.context.scene.render.pixel_aspect_y = 1
                bpy.context.scene.render.resolution_percentage = 100
                bpy.context.scene.render.resolution_x = 2080
                bpy.context.scene.render.resolution_y = 2080
                bpy.context.scene.eevee.use_shadow_high_bitdepth = True
                bpy.context.scene.eevee.use_soft_shadows = True
                bpy.context.scene.eevee.shadow_cube_size = '2048'
                bpy.context.scene.eevee.shadow_cascade_size = '2048'
                bpy.context.scene.eevee.shadow_method = 'VSM'
                bpy.context.scene.eevee.taa_render_samples = 25

                
                if save_images:
                    if asymmetric:
                        f_name = "asym_"
                    else:
                        f_name = "sym_"
                    if c == 0:
                        f_name = f_name + '3D_ort'
                    else:
                        f_name = f_name + '3D_per'
                    
                    f_num = 1;
                    write_name = os.path.join(path_dir, f_name + '_' +str(f_num).zfill(3) + suffix + '.png' )
                    while os.path.exists(write_name):
                        f_num = f_num + 1
                        write_name = os.path.join(path_dir, f_name + '_' + str(f_num).zfill(3) + suffix + '.png' )
                    
                    if c == 0 and rotated:
                        first = False
                        bpy.ops.export_scene.obj(filepath=write_name.replace('png','obj').replace('_3D_ort','').replace('b.','.'))
                        bpy.ops.export_mesh.stl(filepath=write_name.replace('png','stl').replace('_3D_ort','').replace('b.','.'))
                    
                    bpy.context.scene.render.filepath = write_name
                
                    # now render
                    bpy.ops.render.render(write_still=True)
                    # load image to make flat versions
                    img=plt.imread(write_name)
                    img_cp = img.copy()
                    
                    bg_color = img[0,0,:].reshape(1,1,4)
                    bg_img = np.ones_like(img)*bg_color
                    dif_img = img-bg_color
                    ob_mask = np.any(dif_img > .005, axis=-1)

                    # custom background color
                    new_bg = np.ones((1,1,1,4))*(70/255, 70/255, 70/255, 0)

                    # replace object pixels with average over pixels
                    img_cp[ob_mask] = np.average(img[ob_mask],0)
                    img_cp[~ob_mask] = new_bg
                    # make background transparent, and the same for every object	
                    img[~ob_mask] = new_bg

                    # write original image
                    plt.imsave(write_name, img)

                    # and copy
                    write_name = write_name.replace('3D_per','2D_per')
                    write_name = write_name.replace('3D_ort','2D_ort')
                    plt.imsave(write_name, img_cp)

# main function starts here

def main():

    import argparse, sys    

    # get the args passed to blender after "--", all of which are ignored by
    # blender so scripts may receive their own arguments
    argv = sys.argv
    
    if "--" not in argv:
        argv = []  # as if no args are passed
    else:
        argv = argv[argv.index("--") + 1:]  # get all args after "--"
    
    # When --help or no args are given, print this help
    usage_text = (
        "Run blender in background mode with this script:"
        "  blender --background --python " + __file__ + " -- [options]"
    )
    
    parser = argparse.ArgumentParser(description=usage_text)
    parser.add_argument(
        "--asymmetric", help="Make asymmetric objects?  \n(default: True)", action="store_true")
    parser.add_argument(
        "--num_exemplars", metavar="float", type=int, default=1, help="How many exemplars to generate?")
    parser.add_argument(
        "--min_dist", metavar="float", type=float, default=0.05, help="Minimum distance from symmetry axis of each new metaball")
    parser.add_argument(
        "--dont_save", help="Pass in order to NOT save images to file \n(default: images are saved)", action="store_false")  
    parser.add_argument(
        "--bg_color", help="Background color  \n(default: (.05, .05, .05, 1)", metavar="str", type=str, default=(.05, .05, .05)) 
    parser.add_argument(
        "--ob_color", help="Object color  \n(default: (1, 1, 1, 1)", metavar="str", type=str, default=(1, 1, 1, 1)) 
    parser.add_argument(
        "--out_dir", metavar="str", type=str,default="/Users/kohler/Google Drive/ONGOING/Symmetry_3D/blender_blobs/scripted_blobs/",
         nargs="?", help="Full path to image output directory  \n(default: /Users/kohler/Google Drive/ONGOING/Symmetry_3D/blender_blobs/scripted_blobs)")
    
    args = parser.parse_args(argv)
    
    if not argv:
        parser.print_help()
        return

    # Run the example function
    for x in range(args.num_exemplars):
    	make_objects(asymmetric=args.asymmetric, min_dist=args.min_dist, save_images=args.dont_save, bg_color=args.bg_color, ob_color=args.ob_color, out_dir=args.out_dir)

    if args.asymmetric:
    	print("Finished! Made {0} asymmetric objects".format(args.num_exemplars))
    else:
    	print("Finished! Made {0} symmetric objects".format(args.num_exemplars))
    
if __name__ == "__main__":
    main()
# argv = sys.argv
# argv = argv[argv.index("--") + 1:]  # get all args after "--"

# if len(argv) < 6:
#     argv[5] = "/Users/kohler/Google Drive/ONGOING/Symmetry_3D/blender_blobs/scripted_blobs"
# if len(argv) < 5:
#     argv[4] = (1, 1, 1, 1)
# if len(argv) < 4:
#     argv[3] = (.05, .05, .05, 1)
# if len(argv) < 3:
#     argv[2] = True
# if len(argv) < 2:
#     argv[1] = 0.05
# if len(argv) < 1: 
#     argv[0] = True
# main(symmetric=argv[0], min_dist=argv[1], save_images=argv[2], bg_color=argv[3], ob_color=argv[4], out_dir=argv[5])

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description=
#         " \n"
#         "###############################################################\n"
#         "Wrapper function for easy opening of SUMA viewer.\n"
#         "Supports opening suma surfaces both in native and std141 space.\n"
#         "Supports opening a volume file in afni, linked to the surfaces,\n"
#         "via the --openvol and --surfvol options. If surfvol is given,  \n"
#         "openvol will be assumed. Note that when a volume file is given,\n"
#         "script will change to its directory.                           \n"
#         "\n"
#         "Author: pjkohler, Stanford University, 2016                    \n"
#         "###############################################################\n"
#         ,formatter_class=argparse.RawTextHelpFormatter,usage=argparse.SUPPRESS)
#     parser.add_argument(
#         "symmetric",type=str, nargs="?", help="Subject ID (without '_fs4')") 
#     parser.add_argument(
#         "--hemi", metavar="float", type=float, default=0.05, help="Minimum distance from symmetry axis of each new metaball")
#     parser.add_argument(
#         "--save_images", help="Save images to file?  \n(default: on)", action="store_true")  
#     parser.add_argument(
#         "--bg_color", help="Background color  \n(default: (.05, .05, .05, 1)", metavar="str", type=str, default=(.05, .05, .05, 1)) 
#     parser.add_argument(
#         "--ob_color", help="Object color  \n(default: (1, 1, 1, 1)", metavar="str", type=str, default=(1, 1, 1, 1)) 
#     parser.add_argument(
#         "--out_dir", metavar="str", type=str,default=None,
#          nargs="?", help="Full path to image output directory  \n(default: /Users/kohler/Google Drive/ONGOING/Symmetry_3D/blender_blobs/scripted_blobs)")
#     if len(sys.argv)==1:
#         parser.print_help()
#         sys.exit(1)
#     args = parser.parse_args()
# mball_maker_v2(symmetric=args.symmetric, min_dist=args.min_dist, save_images=args.save_images, bg_color=args.bg_color, ob_color=args.ob_color, out_dir=args.out_dir)