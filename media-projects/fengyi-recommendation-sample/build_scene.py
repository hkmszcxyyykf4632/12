import bpy
import math
import json
import random
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / 'timing.json').read_text(encoding='utf-8'))
FPS = 24
random.seed(40521)
bpy.ops.wm.read_factory_settings(use_empty=True)
print('Building local scene', flush=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = math.ceil(DATA['duration'] * FPS)
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.render.filepath = str(ROOT / 'frames' / '')
scene.render.threads_mode = 'FIXED'
scene.render.threads = 8
scene.eevee.taa_render_samples = 32
scene.world = bpy.data.worlds.new('Warm studio environment')
scene.world.color = (.3, .3, .3)
scene.world.use_nodes = True
scene.world.node_tree.nodes.get('Background').inputs[0].default_value = (.32, .38, .41, 1)
scene.world.node_tree.nodes.get('Background').inputs[1].default_value = .30
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'


def mat(name, color, rough=.6, metal=0, bump=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bs = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal
    if bump:
        noise = m.node_tree.nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 110
        noise.inputs['Detail'].default_value = 2
        b = m.node_tree.nodes.new('ShaderNodeBump')
        b.inputs['Strength'].default_value = bump
        b.inputs['Distance'].default_value = .025
        m.node_tree.links.new(noise.outputs['Fac'], b.inputs['Height'])
        m.node_tree.links.new(b.outputs['Normal'], bs.inputs['Normal'])
    return m


M = {
    'brown': mat('Chief • warm chestnut fleece', (.115, .043, .014), .82, bump=.3),
    'white': mat('Angel • ivory fleece', (.89, .84, .72), .88, bump=.24),
    'skin': mat('Soft peach vinyl', (.84, .57, .34), .53),
    'angel_skin': mat('Pale peach vinyl', (.96, .71, .51), .5),
    'pink': mat('Ear blush', (.72, .36, .27), .72),
    'whitepink': mat('Warm inner ear', (.91, .62, .49), .72),
    'eyes': mat('Warm eye white', (.95, .92, .80), .31),
    'iris': mat('Amber iris', (.35, .18, .045), .26),
    'silvereye': mat('Soft gray iris', (.25, .29, .31), .28),
    'pupil': mat('Deep glossy pupil', (.013, .011, .009), .18),
    'glint': mat('Eye catchlight', (1, 1, .95), .1),
    'mouth': mat('Mouth interior', (.085, .022, .015), .86),
    'tongue': mat('Tongue', (.69, .26, .25), .65),
    'teeth': mat('Small ivory teeth', (.99, .93, .78), .4),
    'gold': mat('Satin gold', (.66, .37, .085), .28, .75),
    'wing': mat('Soft silver wings', (.58, .64, .65), .35, .65),
    'wood': mat('Walnut table', (.23, .107, .045), .44, bump=.16),
    'wall': mat('Muted sage wall', (.27, .35, .28), .92),
    'floor': mat('Warm plaster', (.52, .43, .31), .88),
    'cloth': mat('Oatmeal upholstery', (.66, .51, .32), .9, bump=.24),
    'leaf': mat('Plant green', (.12, .22, .085), .72),
    'pot': mat('Stoneware', (.63, .47, .29), .83),
}


def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    scene.collection.objects.link(o)
    o.location = loc
    if parent:
        o.parent = parent
    return o


def uv(name, loc, scale, material, parent=None, seg=40, rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.materials.append(material)
    for p in o.data.polygons:
        p.use_smooth = True
    if parent:
        o.parent = parent
    return o


def cube(name, loc, scale, material, bevel=.08):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    if bevel:
        b = o.modifiers.new('Soft edges', 'BEVEL')
        b.width = bevel
        b.segments = 3
        o.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
    return o


def curve(name, pts, radius, material, parent=None):
    c = bpy.data.curves.new(name, 'CURVE')
    c.dimensions = '3D'
    c.bevel_depth = radius
    c.bevel_resolution = 3
    s = c.splines.new('BEZIER')
    s.bezier_points.add(len(pts) - 1)
    for p, v in zip(s.bezier_points, pts):
        p.co = v
        p.handle_left_type = p.handle_right_type = 'AUTO'
    o = bpy.data.objects.new(name, c)
    scene.collection.objects.link(o)
    o.data.materials.append(material)
    if parent:
        o.parent = parent
    return o


def fuzz(name, center, scale, material, parent, count, seed, length=.055):
    rng = random.Random(seed)
    verts, faces = [], []
    for k in range(count):
        z = rng.uniform(-1, 1)
        a = rng.uniform(0, math.tau)
        r = math.sqrt(1 - z * z)
        n = Vector((r * math.cos(a), r * math.sin(a), z))
        p = Vector(center) + Vector((n.x * scale[0], n.y * scale[1], n.z * scale[2]))
        norm = Vector((n.x / scale[0], n.y / scale[1], n.z / scale[2])).normalized()
        tangent = norm.cross(Vector((0, 0, 1)))
        if tangent.length < .01:
            tangent = Vector((1, 0, 0))
        tangent.normalize()
        bit = tangent.cross(norm).normalized()
        width = rng.uniform(.006, .011)
        h = length * rng.uniform(.6, 1.3)
        idx = len(verts)
        verts.extend([p + tangent * width, p + bit * width, p - tangent * width, p - bit * width, p + norm * h + tangent * .01])
        faces.extend([(idx, idx + 1, idx + 4), (idx + 1, idx + 2, idx + 4), (idx + 2, idx + 3, idx + 4), (idx + 3, idx, idx + 4)])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(material)
    o = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(o)
    o.parent = parent
    for p in mesh.polygons:
        p.use_smooth = True
    return o


def connect(o, a, b, width):
    a, b = Vector(a), Vector(b)
    o.location = (a + b) * .5
    o.rotation_euler = (b - a).to_track_quat('Z', 'Y').to_euler()
    o.scale = (width, width, (b - a).length * .56)


def wing(parent, sign):
    pts = [(.52, .18, 2.35), (.85, .20, 2.72), (1.22, .14, 2.31), (1.33, .08, 1.92), (1.04, .08, 2.08), (.85, .10, 1.91), (.67, .13, 2.06)]
    pts = [(sign * x, y, z) for x, y, z in pts]
    mesh = bpy.data.meshes.new('Silver wing membrane')
    mesh.from_pydata(pts, [], [tuple(range(7))])
    mesh.materials.append(M['wing'])
    o = bpy.data.objects.new('Silver wing', mesh)
    scene.collection.objects.link(o)
    o.parent = parent
    solid = o.modifiers.new('Membrane depth', 'SOLIDIFY')
    solid.thickness = .04
    b = o.modifiers.new('Rounded membrane', 'BEVEL')
    b.width = .035
    b.segments = 3
    curve('Wing rim', pts + [pts[0]], .028, M['wing'], parent)
    for i in (2, 3, 4, 5):
        curve('Wing rib', [pts[0], pts[1], pts[i]], .017, M['wing'], parent)


def make_actor(name, x, angel=False):
    root = empty(name, (x, 0, 0))
    fm = M['white' if angel else 'brown']
    skin = M['angel_skin' if angel else 'skin']
    uv(name + ' torso', (0, .08, 1.91), (.63, .47, .71), fm, root)
    fuzz(name + ' body fleece', (0, .08, 1.91), (.63, .47, .71), fm, root, 4800, 101 if angel else 100, .047)
    head = empty(name + ' expressive head', (0, -.01, 2.94), root)
    uv(name + ' head', (0, 0, 0), (1, .66, .86), fm, head)
    fuzz(name + ' head fleece', (0, 0, 0), (1, .66, .86), fm, head, 12500, 8 if angel else 7, .057)
    for sign in [-1, 1]:
        e = empty(name + ' ear', (sign * .45, .04, .86), head)
        e.rotation_euler[1] = sign * .1
        uv('Long outer ear', (0, 0, .48), (.24, .225, .7), fm, e)
        fuzz('Ear fleece', (0, 0, .48), (.24, .225, .7), fm, e, 1700, (23 if angel else 21) + sign, .04)
        uv('Peach inner ear', (0, -.184, .5), (.134, .067, .51), M['whitepink' if angel else 'pink'], e)
    uv('Peach face', (0, -.54, -.08), (.84, .205, .625), skin, head)
    eyes = []
    brows = []
    for sign in [-1, 1]:
        eye = empty('Animated eye', (sign * .326, -.708, .12), head)
        uv('Eye white', (0, 0, 0), (.252, .088, .292), M['eyes'], eye)
        iris = empty('Gaze', (-sign * .012, -.075, -.01), eye)
        uv('Iris', (0, 0, 0), (.148, .047, .218), M['silvereye' if angel else 'iris'], iris)
        uv('Pupil', (0, -.038, .008), (.102, .028, .167), M['pupil'], iris)
        uv('Soft eye sparkle', (-.036, -.061, .081), (.037, .012, .052), M['glint'], iris, seg=20, rings=12)
        uv('Tiny eye sparkle', (.041, -.063, -.062), (.018, .01, .024), M['glint'], iris, seg=16, rings=10)
        brow = curve('Soft expressive brow', [(sign * .09, -.729, .423), (sign * .32, -.742, .465), (sign * .55, -.70, .418)], .024, skin, head)
        eyes.append((eye, iris))
        brows.append(brow)
    uv('Small nose', (0, -.836, -.045), (.078, .065, .055), M['pupil'], head)
    mouth = empty('Talking mouth', (0, -.733, -.333), head)
    cavity = uv('Mouth opening', (0, 0, 0), (.356, .044, .066), M['mouth'], mouth)
    teeth = empty('Upper teeth', (0, -.042, 0), mouth)
    for i in range(9):
        x0 = -.28 + i * .07
        z0 = .023 + .035 * (x0 / .28) ** 2
        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=.004, radius2=.035, depth=.078, location=(x0, 0, z0))
        tooth = bpy.context.object
        tooth.name = 'Small pointed tooth'
        tooth.scale.y = .52
        tooth.parent = teeth
        tooth.data.materials.append(M['teeth'])
        for f in tooth.data.polygons:
            f.use_smooth = True
    tongue = uv('Tongue detail', (0, -.049, -.055), (.13, .018, .023), M['tongue'], mouth)
    arms = []
    for sign in [-1, 1]:
        upper = uv('Upper arm', (0, 0, 0), (1, 1, 1), fm, root, seg=32, rings=20)
        lower = uv('Forearm', (0, 0, 0), (1, 1, 1), fm, root, seg=32, rings=20)
        hand = empty('Expressive paw', (0, 0, 0), root)
        uv('Paw palm', (0, 0, 0), (.20, .115, .12), skin, hand)
        for j in range(3):
            uv('Rounded finger', ((j - 1) * .105, -.067, .004), (.067, .105, .08), skin, hand, seg=24, rings=16)
        uv('Thumb', (sign * .16, -.015, .055), (.09, .085, .08), skin, hand, seg=24, rings=16)
        arms.append((sign, upper, lower, hand))
    if angel:
        wing(root, -1)
        wing(root, 1)
    else:
        curve('Gold necklace', [(-.38, -.38, 2.34), (-.23, -.52, 2.16), (0, -.57, 2.09), (.23, -.52, 2.16), (.38, -.38, 2.34)], .024, M['gold'], root)
        uv('Gold medallion', (0, -.60, 2.02), (.135, .035, .157), M['gold'], root)
        curve('Medallion mark', [(-.055, -.64, 2.005), (0, -.645, 2.105), (.055, -.64, 2.005)], .012, M['wood'], root)
    return {'name':name, 'root':root,'head':head,'eyes':eyes,'brows':brows,'cavity':cavity,'teeth':teeth,'tongue':tongue,'arms':arms,'angel':angel}


cube('Back wall', (0, 2.4, 3), (16, .15, 7), M['wall'])
cube('Room floor', (0, 0, -.07), (18, 18, .12), M['floor'])
cube('Floating walnut shelf', (0, 2.05, 2.97), (8.6, .6, .13), M['wood'])
cube('Lower wall trim', (0, 2.27, .5), (16, .12, .06), M['wood'], .01)
for x in [-3.3, 3.4]:
    uv('Stoneware planter', (x, 1.9, 3.23), (.27, .27, .3), M['pot'])
    for i in range(8):
        a = i * 2.39
        p = (x + .26 * math.cos(a), 1.9 + .15 * math.sin(a), 3.48 + i * .035)
        curve('Plant stem', [(x, 1.9, 3.35), p], .017, M['leaf'])
        leaf = uv('Plant leaf', p, (.17, .055, .08), M['leaf'])
        leaf.rotation_euler[1] = -.4
        leaf.rotation_euler[2] = a
for i, x in enumerate([-.58, -.35, -.17, .08, .31, .55]):
    book = mat('Book ' + str(i), [(.55,.35,.17),(.69,.65,.49),(.18,.25,.19)][i%3], .88)
    cube('Shelf book', (x, 1.93, 3.29), (.14, .32, .50 + .07 * (i%3)), book, .012)
for x in [-1.6, 1.6]:
    uv('Rounded chair back', (x, .49, 1.82), (.83, .2, .98), M['cloth'])
    uv('Seat', (x, .12, .99), (.74, .65, .16), M['cloth'])
    cube('Chair leg', (x-.4, .2, .53), (.09,.09,.9), M['wood'], .025)
    cube('Chair leg', (x+.4, .2, .53), (.09,.09,.9), M['wood'], .025)
actors = [make_actor('chief', -1.6), make_actor('angel', 1.6, True)]
print('Both character rigs created', flush=True)
uv('Oval walnut tabletop', (0, -.70, 1.28), (3.55, 1.12, .105), M['wood'], seg=96, rings=24)
cube('Table pedestal', (0, -.55, .63), (.9, .7, 1.22), M['wood'], .18)


def area(name, loc, energy, color, size, target):
    bpy.ops.object.light_add(type='AREA', location=loc)
    o = bpy.context.object
    o.name = name
    o.data.energy = energy
    o.data.color = color
    o.data.shape = 'DISK'
    o.data.size = size
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()


area('Window key', (-3.6, -4.4, 6.7), 650, (1, .82, .62), 5, (0, 0, 2.7))
area('Soft fill', (4, -3, 4.8), 380, (.78, .88, 1), 4, (0, 0, 2.7))
area('Warm rim', (1, 1.8, 6), 700, (1, .78, .50), 3, (0, 0, 3))
bpy.ops.object.camera_add(location=(0, -12.8, 4.8))
cam = bpy.context.object
cam.name = 'Conversation camera'
cam.rotation_euler = (Vector((0, -.03, 2.72)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.type = 'PERSP'
cam.data.lens = 50
focus = empty('Focus on the hosts', (0, -.5, 2.9))
cam.data.dof.use_dof = True
cam.data.dof.focus_object = focus
cam.data.dof.aperture_fstop = 3.5
scene.camera = cam


def smooth(a):
    a = max(0, min(1, a))
    return a * a * (3 - 2 * a)


def bump(t, a, b, attack=.18, release=.24):
    return smooth((t-a)/attack) * smooth((b-t)/release)


def speech(speaker, t):
    for seg in DATA['segments']:
        u = t - seg['start']
        if seg['speaker'] == speaker and 0 <= u <= seg['duration']:
            env = seg['envelope']
            idx = int(u * 100)
            energy = sum(env[max(0,min(len(env)-1,idx+k))] * w for k,w in [(-2,.12),(-1,.22),(0,.32),(1,.22),(2,.12)])
            opening = min(1, max(0, energy * 5.5 - .02))
            char = ''
            for word in seg['words']:
                wu = u - word['start']
                if 0 <= wu <= word['duration']:
                    txt = word['text']
                    char = txt[min(len(txt)-1, int(wu/max(.01,word['duration'])*len(txt)))]
                    break
            roundness = 1 if char in '博洛乌有球' else (.5 if char in '喂么什二' else 0)
            closed = char in '买半' and u % .15 < .028
            return opening * (.30 if closed else 1), roundness, seg
    return 0, 0, None


animated = []
for a in actors:
    animated.extend([a['head'],a['cavity'],a['teeth'],a['tongue']])
    animated.extend(o for pair in a['eyes'] for o in pair)
    animated.extend(a['brows'])
    animated.extend(o for _,u,l,h in a['arms'] for o in (u,l,h))

for frame in range(1, scene.frame_end + 1):
    t = (frame - 1) / FPS
    for actor in actors:
        name = actor['name']
        is_a = actor['angel']
        opening, roundness, current = speech(name,t)
        own = [s for s in DATA['segments'] if s['speaker']==name]
        speaking = sum(bump(t,s['start']-.12,s['start']+s['duration']+.1) for s in own)
        gaze_dir = -1 if is_a else 1
        actor['head'].rotation_euler = (
            .025 * math.sin(t*1.4 + (1.2 if is_a else 0)) + .026*speaking*math.sin(t*5.2),
            gaze_dir * (.016 + .015*math.sin(t*1.8)),
            gaze_dir * (.17 + .025*math.sin(t*1.5))
        )
        actor['head'].location.z = 2.94 + .012*math.sin(t*2.1 + (2 if is_a else 0))
        actor['cavity'].scale = (.354-.09*roundness*opening, .044, .060 + .17*opening)
        actor['teeth'].location.z = .02 + .082*opening
        actor['teeth'].scale.x = 1 - .18*roundness*opening
        actor['tongue'].location.z = -.035 - .125*opening
        actor['tongue'].scale.z = .023 * opening
        blink = 0
        for bt in ([1.1,4.7,8.2,10.3] if is_a else [2.8,6.0,9.35]):
            blink = max(blink, max(0, 1-abs(t-bt)/.10))
        for eye, iris in actor['eyes']:
            eye.scale.z = 1 - .94*blink
            iris.location.x = gaze_dir * .04
        for i,brow in enumerate(actor['brows']):
            eyebrow = .013*speaking
            if current and current['speaker']=='chief':
                eyebrow += .017*bump(t,current['start'],current['start']+.55)
            brow.location.z = eyebrow*(1 if i==0 else .7)
        gesture = 0
        for turn,s in enumerate(own):
            strength = ([.56,.86,.26] if is_a else [.85,.33,.48])[turn]
            gesture += strength*bump(t,s['start']+.02,s['start']+s['duration']+.22,.28,.38)
        for sign, upper, lower, hand in actor['arms']:
            dominant = sign == (-1 if is_a else 1)
            g = gesture * (1 if dominant else .08)
            shoulder = (sign*.52, .0, 2.09)
            elbow = (sign*(.67+.12*g), -.22-.10*g, 1.72+.13*g)
            paw = (sign*(.48+.35*g), -.72+.05*g, 1.48+.56*g)
            connect(upper,shoulder,elbow,.19)
            connect(lower,elbow,paw,.17)
            hand.location = paw
            hand.rotation_euler = (.15+.95*g, sign*(-.1-.3*g), sign*(.1+.25*g))
    for o in animated:
        o.keyframe_insert('location', frame=frame)
        o.keyframe_insert('rotation_euler', frame=frame)
        o.keyframe_insert('scale', frame=frame)

for action in bpy.data.actions:
    for fc in action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'

(ROOT/'frames').mkdir(exist_ok=True)
print('Animation keyframes ready', flush=True)
scene.frame_set(25)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'fengyi-hosts.blend'))
scene.render.filepath = str(ROOT/'scene-review.png')
bpy.ops.render.render(write_still=True)
print('READY', ROOT/'fengyi-hosts.blend', 'FRAMES',scene.frame_end)
