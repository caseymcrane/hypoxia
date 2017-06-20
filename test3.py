import libtcodpy as libtcod
import math
import textwrap

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT

MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1
INVENTORY_WIDTH = 50

MAP_WIDTH = 80
MAP_HEIGHT = 43

ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30
MAX_ROOM_ITEMS = 2
MAX_ROOM_MONSTERS = 3

#field of view variables
FOV_ALGO = 0
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10

LIMIT_FPS = 20

FLYING_LIMB = ['<','^','>','v','<','^','>','v']



color_dark_wall = libtcod.Color(0, 0, 100)
color_light_wall = libtcod.Color(130, 110, 50)
color_dark_ground = libtcod.Color(50, 50, 150)
color_light_ground = libtcod.Color(200, 180, 50)

#class for making rectangle objects to carve out rooms
class Rect:

        #constructor
        def __init__(self,x,y,w,h):
                self.x1 = x
                self.y1 = y
                self.x2 = x + w
                self.y2 = y + h
                
        def center(self):
                center_x = (self.x1 + self.x2)/2
                center_y = (self.y1 + self.y2)/2
                return(center_x,center_y)

        def intersect(self,other):
                #returns true if this rect intersects with the other one
                return(self.x1 <= other.x2 and self.x2 >= other.x1 and self.y1 <= other.y2 and self.y2 >= other.y1)

def create_room(room):
        global map
        #carve out the room by going through the map and making the tiles passable
        for x in range(room.x1+1, room.x2):
                for y in range(room.y1+1, room.y2):
                        map[x][y].blocked = False
                        map[x][y].block_sight = False

def create_h_tunnel(x1,x2,y):
        #commented out global map because its maybe redundant
        #global map
        for x in range(min(x1,x2),max(x1,x2)+1):
                map[x][y].blocked = False
                map[x][y].block_sight = False

def create_v_tunnel(y1,y2,x):
        #commented out global map because its maybe redundant
        #global map
        for y in range(min(y1,y2),max(y1,y2)+1):
                map[x][y].blocked = False
                map[x][y].block_sight = False

class Tile:
        def __init__(self,blocked,block_sight=None):
                self.blocked = blocked

                self.explored = False

                #check if a tile blocks sight. if it does, have it block movement as well
                if block_sight is None: block_sight = blocked
                self.block_sight = block_sight

class Object:
        #this is a generic object, anything you can see
        def __init__(self,x,y,char,name,color,blocks=False,body=None,item=None, mangle_function = None, death_function = None):
                self.name = name
                self.blocks = blocks
                self.x = x
                self.y = y
                self.char = char
                self.color = color

                self.body = body
                if self.body:
                        self.body.owner = self

                self.item = item
                if self.item:
                        self.item.owner = self

        def move(self,dx,dy):
                if not is_blocked(self.x+dx,self.y+dy):
                        self.x += dx
                        self.y += dy

        def move_towards(self,target_x,target_y):
                dx = target_x - self.x
                dy = target_y - self.y
                #we use squared distance instead of taking sqrt. much cheaper
                dist = math.sqrt(dx ** 2 + dy ** 2)

                dx=int(round(dx/dist))
                dy=int(round(dy/dist))

                self.move(dx,dy)

        def move_astar(self,target):
                libtcod.map_new(MAP_WIDTH,MAP_HEIGHT)
                for y1 in range(MAP_HEIGHT):
                        for x1 in range(MAP_WIDTH):
                                libtcod.map_set_properties(fov, x1, y1, not map[x1][y1].block_sight, not map[x1][y1].blocked)
                                
                for obj in objects:
                        if obj.blocks and obj!=self and obj!=target:
                                libtcod.map_set_properties(fov,obj.x,obj.y,True,False)
                                
                                #ASTAR TUTORIAL         
                
        def distance_to(self, other):
                dx = other.x - self.x
                dy = other.y - self.y
                return math.sqrt(dx ** 2 + dy ** 2)

        #send obj to back of the object list to help with dead monsters overlapping live ones
        def send_to_back(self):
                global objects;
                objects.remove(self)
                objects.insert(0,self)

        def draw(self):
                #the object basically handles its own rendering here
                libtcod.console_set_default_foreground(con,self.color)
                libtcod.console_put_char(con,self.x,self.y,self.char,libtcod.BKGND_NONE)

        def clear(self):
                #handle the deletion and cleanup routine. for now just replace with whitespace
                libtcod.console_put_char(con,self.x,self.y,' ',libtcod.BKGND_NONE)

##############################################################################################
#       COMPONENT DEFINITIONS
#############################################################################################

class BasicMonster:
        def take_turn(self):
                monster = self.owner
                if libtcod.map_is_in_fov(fov_map,monster.x,monster.y):
                        if monster.distance_to(player) >= 2:
                                monster.move_towards(player.x, player.y)

                        elif player.fighter.hp > 0:
                                monster.fighter.attack(player)

##!!!!EXPERIMENTAL NEXT GENERATION BODY SYSTEM!!!!##

class Body:
        def __init__(self,limbs=[],organs=[],inventory=[],blood=None):
                self.limbs = limbs
                self.organs = organs
                self.inventory = inventory
                self.blood = blood
                
                if len(limbs):
                        for l in limbs:
                                l.owner = self
                                        
                if len(organs):
                        for o in organs:
                                o.owner = self
                
        def take_damage(self,damage):
                if damage > 0:
                        if libtcod.random_get_int(0,0,10)<7:
                                self.limbs[0].take_damage(damage)
                                return self.limbs[0]
                        else:
                                rng_limb = libtcod.random_get_int(0,1,5)
                                self.limbs[rng_limb].take_damage(damage)
                                return self.limbs[rng_limb]
                                
        def move_or_attack(self,dx,dy):

                # coords the player is moving/attacking towards
                x = self.owner.x + dx
                y = self.owner.y + dy

                # try to find an attackable obj
                target = None
                for object in objects:
                        if object.body and object.x == x and object.y == y:
                                target = object
                                break

                # attack if you found a target, otherwise move
                if target is not None:
                        for limb in self.limbs:
                                if limb.attack_function is not None:
                                        limb.attack_function(limb, self.owner, target)
                                        break
                                
                self.owner.move(dx,dy)
                                
class Limb:
        def __init__(self,hp,name,strength=None,speed=None,organs=[],grasp=None,equip=None,grab_function=None,attack_function=None,take_damage=None, death_function=None):
                self.name = name
                self.max_hp = hp
                self.hp = hp
                self.strength = strength
                self.speed = speed
                self.grasp = grasp
                self.equip = equip
                self.grab_function = grab_function
                self.attack_function = attack_function

                self.death_function = death_function

                self.organs = organs
                
                if len(organs):
                        for o in organs:
                                o.owner = self.owner
                                        
        def take_damage(self,damage):
#               if damage > max_hp/2:
                if damage > 0:
                        self.hp -= damage
                        function = self.death_function
                        if function is not None:
                                function(self.owner)
                if self.hp <= 0:
                        d_function = self.death_function
                        if d_function is not None:
                                d_function(self.owner)

        
##############################################################################################
##################                      LIMB COMPONENT FUNCTIONS                                                ##################
                                
def grab(self,obj):
        if self.strength > obj.weight:
                self.grasp = obj
                        
def attack(self, attacker, target):
        if target.body is not None:
                if self.grasp is not None:
                        limb = target.body.take_damage(self.strength*self.grasp.force_mult+self.grasp.damage)
                        message(attacker.name + ' attacks ' + limb.name + ' with the ' + attacker.grasp.name + ' for ' + str(self.strength*self.grasp.force_mult+self.grasp.damage) + ' damage!')
                else:
                        limb = target.body.take_damage(self.strength)
                        message(attacker.name + ' punches ' + limb.name + ' for ' + str(self.strength) + ' damage!', libtcod.red)
                        message('DEBUG ' + limb.name + ": " + str(limb.hp) + ' out of ' + str(limb.max_hp),libtcod.yellow)
                        
                        
##############################################################################################
##################                      LIMB DEATH FUNCTIONS                                                ##################

#just a placeholder so i can make sure people actually die in combat
def dummydeath(monster):
        monster.owner.char = '%'
        monster.owner.color = libtcod.dark_red
        monster.owner.blocks = False
        monster.owner.name = 'mangled corpse of a ' + monster.owner.name
        monster.owner.send_to_back()
        monster.owner.body = None

                                
##############################################################################################
##############                                          ORGANS
                                
class Brain:
        def __init__(self,name,hp,iq=None,fear=None,algo=None,strategy=None):
                self.name = name
                self.max_hp = hp
                self.hp = hp
                self.iq = iq
                self.algo = algo
                self.strategy = strategy
                self.fear = fear
                
        def take_turn(self):
                if self.algo == 'A*':
                        monster = self.owner
                        if libtcod.map_is_in_fov(fov_map,monster.x,monster.y):
                                if monster.distance_to(player)>=2:
                                        monster.move_astar(player)
                                        
                                        
                                #later on i want to change this pounce condition to somehow relate to perceived weakness or fear or something
                                elif player.body is not None:
                                        for limb in monster.body.limbs:
                                                if limb.attack_function is not None:
                                                        limb.attack_function(limb, monster, player)
                                                        
                                                        #a vicious enemy will not break, and will attack with every limb they have
                                                        if strategy != 'vicious':
                                                                break

class Heart:
        def __init__(self,hp,heal,fault):
                self.max_hp = hp
                self.hp = hp
                self.heal = heal
                self.fault = fault
                
        def beat(owner, heal):
                plr = self.owner
                plr.hp += heal
                if plr.head:
                        plr.head.hp += heal
                if plr.l_arm:
                        plr.l_arm.hp += heal
                if plr.r_arm:
                        plr.r_arm.hp += heal
                if plr.l_leg:
                        plr.l_leg.hp += heal
                if plr.r_leg:
                        plr.r_leg.hp += heal

        def take_damage(self, damage):
                if damage > 0:
                        self.hp -= damage
                if libtcod.random_get_int(0,0,100)<self.fault:
                        function = self.death_function
                        if function is not None:
                                function(self.owner)


class Eyes:
        def __init__(self,hp,color,vision,special):
                self.max_hp = hp
                self.hp = hp
                self.color = color
                self.vision = vision
                self.special = special
                
        def take_damage(self,damage):
                if damage > 0:
                        self.hp -= damage
                if self.hp <= 0:
                        function = self.death_function
                        if function is not None:
                                function(self.owner)

class Blood:
        def __init__(self,color,volume,pressure,effect=None):
                self.color = color
                self.effect = effect
                self.volume = volume
                self.pressure=pressure
                self.effect=effect
        

##############################################################################################
#######                                 INITIALIZING BODIES
##############################################################################################

def create_human_at_pos(x, y, char, color, name, strength, hp, speed, inventory=[]):
                
        torso = Limb(3*hp/8,name + '\'s torso',strength)
        head = Limb(hp/8 ,name + '\'s head',death_function=dummydeath)
        left_arm = Limb(hp/8,name + '\'s left arm',strength,attack_function = attack,death_function=dummydeath)
        right_arm = Limb(hp/8,name + '\'s right arm',strength,attack_function = attack,death_function=dummydeath)
        left_leg = Limb(hp/8,name + '\'s left leg',speed,death_function=dummydeath)
        right_leg = Limb(hp/8,name + '\'s right leg',speed,death_function=dummydeath)
                
        #here we have the final assembled limb list. organs will form a separate list soon as well
        limb_list = [torso,head,left_arm,right_arm,left_leg,right_leg]
        
        human_body = Body(limb_list, inventory)
        #i've left out the ai component, not only because it's very incompetent, but because this will
        #soon be determined by the brain once organs are more developed
        return Object(x,y,char,name,color,blocks = True, body = human_body)
                


##############################################################################################          
#                                                                       ITEMS
##############################################################################################

class Item:     
        def __init__(self, use_function=None):
                self.use_function = use_function


        def pick_up(self, player):
                
                #we have to use player.body.inventory because we don't have a global inventory
                if len(player.body.inventory) >= 26:
                        message('Your inventory is too full to pick up ' + self.owner.name + '.', libtcod.red)
                else:
                        player.body.inventory.append(self.owner)
                        objects.remove(self.owner)
                        message('You found a ' + self.owner.name + '.', libtcod.green)
                        
        def use(self):
                #just call the "use_function" if it is defined
                if self.use_function is None:
                        message('It\s useless.')
                else:
                        if self.use_function() != 'cancelled':
                                inventory.remove(self.owner)  #destroy after use, unless it was cancelled for some reason
                

##############################################################################################
#       MAP INITIALIZATION AND DUNGEON GENERATION
##############################################################################################

def is_blocked(x,y):
        if map[x][y].blocked:
                return True

        for object in objects:
                if object.blocks and object.x == x and object.y == y:
                        return True
        return False

def make_map():
        global map, player

        #fill map with blocked tiles
        map = [[ Tile(True)
                for y in range(MAP_HEIGHT)]
                        for x in range(MAP_WIDTH)]

        rooms = []
        num_rooms = 0

        for r in range(MAX_ROOMS):
                #pick random widths and heights for our rooms
                w = libtcod.random_get_int(0,ROOM_MIN_SIZE,ROOM_MAX_SIZE)
                h = libtcod.random_get_int(0,ROOM_MIN_SIZE,ROOM_MAX_SIZE)
                #and put them in random places, as long as they're within map bounds
                x = libtcod.random_get_int(0,0,MAP_WIDTH - w - 1)
                y = libtcod.random_get_int(0,0,MAP_HEIGHT - h - 1)

                new_room = Rect(x,y,w,h)

                #now check if we're intersecting with any other rooms
                failed = False
                for other_room in rooms:
                        if new_room.intersect(other_room):
                                failed = True
                                break

                #if we have a valid room
                if failed == False:

                        #actually carve it
                        create_room(new_room)
                        (new_x,new_y) = new_room.center()

                        #if it's the first room, spawn the player
                        if num_rooms == 0:
                                player.x = new_x
                                player.y = new_y

                        else:
                        #otherwise, connect to previous room with a tunnel.
                        #first we center on the coords of previous room
                                (prev_x,prev_y) = rooms[num_rooms-1].center()
                                #flip a coin.
                                if libtcod.random_get_int(0,0,1) == 1:
                                        #if heads, horizontal then vertical.
                                        create_h_tunnel(prev_x,new_x,prev_y)
                                        create_v_tunnel(prev_y,new_y,new_x)
                                else:
                                        #tails, and we go vertical then horizontal
                                        create_v_tunnel(prev_y,new_y,prev_x)
                                        create_h_tunnel(prev_x,new_x,new_y)

                        #finally, add the new room to the rooms list
                        place_objects(new_room)
                        rooms.append(new_room)
                        num_rooms += 1


##################################################################################################
#               ROOM POPULATION

def place_objects(room):

        num_monsters = libtcod.random_get_int(0,0,MAX_ROOM_MONSTERS)

        for i in range(num_monsters):
                x=libtcod.random_get_int(0,room.x1+1,room.x2-1)
                y=libtcod.random_get_int(0,room.y1+1,room.y2-1)
                if not is_blocked(x,y):
                        if libtcod.random_get_int(0,0,100) < 60:
                                break
                        else:

                                monster = create_human_at_pos(x,y,'F',libtcod.blue,'frankie',8,90,90)

                        objects.append(monster)
                        
        num_items = libtcod.random_get_int(0,0,MAX_ROOM_ITEMS)
        
        for i in range(num_items):
                x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
                y = libtcod.random_get_int(0, room.y1+1, room.y2-1)

                #only place it if the tile is not blocked
                if not is_blocked(x, y):
                        #create a healing potion
                        item_component = Item()
                        item = Object(x, y, '!', 'healing potion', libtcod.violet, item=item_component)
 
                        objects.append(item)
                        item.send_to_back()  #items appear below other objects
                        
                        
####################################################################################################
###             GUI SETUP
####################################################################################################

#setting a font
libtcod.console_set_custom_font('arial10x10.png',
libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)

#initializing the main window
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'Hypoxia Prototrash', False)

#initializing our off-screen console. drawing to this instead of the root console gives us
#more flexibility in creating GUI layouts and using certain effects, but we have to draw to con from now on
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)

#initializing gui panels
panel = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)

#general purpose status bar
def render_bar(x,y,total_width,name,value,maximum,bar_color,back_color):
        bar_width = int(float(value)/maximum * total_width)

        #first we render the background of the bar
        libtcod.console_set_default_background(panel,back_color)
        libtcod.console_rect(panel,x,y,total_width,1,False,libtcod.BKGND_SCREEN)

        #then the foreground on top
        libtcod.console_set_default_background(panel,bar_color)
        if bar_width > 0:
                libtcod.console_rect(panel,x,y,bar_width,1,False,libtcod.BKGND_SCREEN)

        #then we add text on top for more clarity
        libtcod.console_set_default_foreground(panel, libtcod.white)
        libtcod.console_print_ex(panel,x+total_width/2,y,libtcod.BKGND_NONE, libtcod.CENTER, name + ': ' + str(value) + '/' + str(maximum))

#################################################################################################
#################               MOUSE CONTROL STUFF                     #########################
#################################################################################################

def get_names_under_mouse():
        global mouse

        #return a string with the names of all objects under the mouse
        (x, y) = (mouse.cx, mouse.cy)

        #we also need to make sure they're actually in player's FOV
        names = [obj.name for obj in objects
                if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map,obj.x,obj.y)]

        #now we join and format this list of names, and display it to the player.
        names = ', '.join(names)
        return names.capitalize()

################# DISPLAYING NAMES UNDER MOUSE


####################################################################################################
####    MESSAGE BOX

game_msgs = []

#first we break up incoming messages if necessary into multiple lines, then feed them into the list.
#if the number of messages grows larger than the window height, we cull the top messages
def message(new_msg, color=libtcod.white):
        new_msg_lines = textwrap.wrap(new_msg,MSG_WIDTH)

        for line in new_msg_lines:
                if len(game_msgs) == MSG_HEIGHT:
                        del game_msgs[0]

                game_msgs.append((line,color))



###################################################################################################
###     RENDERING
###################################################################################################

def render_all():
        global fov_map, color_dark_wall, color_light_wall
        global color_dark_ground, color_light_ground
        global fov_recompute

        if fov_recompute:
                fov_recompute = False
                libtcod.map_compute_fov(fov_map,player.x,player.y,TORCH_RADIUS,FOV_LIGHT_WALLS,FOV_ALGO)

        for y in range(MAP_HEIGHT):
                for x in range(MAP_WIDTH):
                        visible = libtcod.map_is_in_fov(fov_map,x,y)
                        wall = map[x][y].block_sight
                        if not visible:
                                if map[x][y].explored:
                                        if wall:
                                                libtcod.console_set_char_background(con,x,y,color_dark_wall,libtcod.BKGND_SET)
                                        else:
                                                libtcod.console_set_char_background(con,x,y,color_dark_ground,libtcod.BKGND_SET)
                        #else, it's visible
                        else:
                                if wall:
                                        libtcod.console_set_char_background(con,x,y,color_light_wall,libtcod.BKGND_SET)
                                else:
                                        libtcod.console_set_char_background(con,x,y,color_light_ground,libtcod.BKGND_SET)
                                map[x][y].explored = True

        #draw all objects, with the player last
        for object in objects:
                if object != player:
                        object.draw()
                player.draw()

###################
## GUI ELEMENTS

        #preparing to render to panel
        libtcod.console_set_default_background(panel, libtcod.black)
        libtcod.console_clear(panel)

        #display the message box
        y=1
        for (line,color) in game_msgs:
                libtcod.console_set_default_foreground(panel,color)
                libtcod.console_print_ex(panel,MSG_X,y,libtcod.BKGND_NONE,libtcod.LEFT,line)
                y+=1

        #show some stats
        #render_bar(1,1,BAR_WIDTH,'HP',player.body.hp,player.body.max_hp,libtcod.light_red,libtcod.darker_red)

        libtcod.console_set_default_foreground(panel,libtcod.light_gray)
        libtcod.console_print_ex(panel,1,0,libtcod.BKGND_NONE,libtcod.LEFT,get_names_under_mouse())


        #blit the panel to the screen
        libtcod.console_blit(panel,0,0,SCREEN_WIDTH,PANEL_HEIGHT,0,0,PANEL_Y)


        #blit our off-screen console
        libtcod.console_blit(con,0,0,MAP_WIDTH,MAP_HEIGHT,0,0,0)

#################################################################################################

#################################################################################################
###     INPUT HANDLING
#################################################################################################


def menu(header, options, width):
        if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')
        header_height = libtcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
        height = len(options) + header_height

        #create an off-screen console that represents the menu's window
        window = libtcod.console_new(width, height)
 
        #print the header, with auto-wrap
        libtcod.console_set_default_foreground(window, libtcod.white)
        libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)

        #print all the options
        y = header_height
        letter_index = ord('a')
        for option_text in options:
                text = '(' + chr(letter_index) + ') ' + option_text
                libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
                y += 1
                letter_index += 1
                
        #blit the contents of "window" to the root console
        x = SCREEN_WIDTH/2 - width/2
        y = SCREEN_HEIGHT/2 - height/2
        libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)

        #present the root console to the player and wait for a key-press
        libtcod.console_flush()
        key = libtcod.console_wait_for_keypress(True)
        
        
        
        
def inventory_menu(header):
        #show a menu with each item of the inventory as an option
        if len(player.body.inventory) == 0:
                options = ['Inventory is empty.']
        else:
                options = [item.name for item in player.body.inventory]
                index = menu(header, options, INVENTORY_WIDTH)




def handle_keys():
        global fov_recompute
        global playerx, playery
        global key

        # movement and combat keys can only be used in the play state
        if game_state == 'playing':
                if key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8:
                        player.body.move_or_attack(0,-1)
                        fov_recompute = True

                elif key.vk == libtcod.KEY_KP7:
                        player.body.move_or_attack(-1,-1)
                        fov_recompute = True

                elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2:
                        player.body.move_or_attack(0,1)
                        fov_recompute = True
                        
                elif key.vk == libtcod.KEY_KP1:
                        player.body.move_or_attack(-1,1)
                        fov_recompute = True

                elif key.vk == libtcod.KEY_LEFT or key.vk == libtcod.KEY_KP4:
                        player.body.move_or_attack(-1,0)
                        fov_recompute = True

                elif key.vk == libtcod.KEY_KP3:
                        player.body.move_or_attack(1,1)
                        fov_recompute = True

                elif key.vk == libtcod.KEY_RIGHT or key.vk == libtcod.KEY_KP6:
                        player.body.move_or_attack(1,0)
                        fov_recompute = True
                        
                elif key.vk == libtcod.KEY_KP9:
                        player.body.move_or_attack(1,-1)
                        fov_recompute = True

        if key.vk == libtcod.KEY_ENTER and key.lalt:
        #Alt+Enter: toggle fullscreen
                libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

        elif key.vk == libtcod.KEY_ESCAPE:
                return 'exit'  #exit game

        else:
                
                #test for other keys
                key_char = chr(key.c)
 
                if key_char == 'g':
                #pick up an item
                        for object in objects:  #look for an item in the player's tile
                                if object.x == player.x and object.y == player.y and object.item:
                                        object.item.pick_up(player)
                                        break
                
                if key_char == 'i':
                        #show the inventory
                        chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
                        if chosen_item is not None:
                                chosen_item.use()
                
                
                return 'didnt-take-turn'

###################     INITIALIZE MOUSE AND KEYBOARD           #################################

mouse = libtcod.Mouse()
key = libtcod.Key()

libtcod.sys_set_fps(LIMIT_FPS)

player = create_human_at_pos(0,0,'@',libtcod.red,'casey',20,20,200)
objects = [player]

#generate the map
make_map()

fov_map = libtcod.map_new(MAP_WIDTH,MAP_HEIGHT)
for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
                libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)


fov_recompute = True

game_state = 'playing'
player_action = None

message('HYPOXIA PROTOTRASH',libtcod.red)

#################################################################################################
###     MAIN LOOP
#################################################################################################

while not libtcod.console_is_window_closed():

        #ayy mouse support bayBEE
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,key,mouse)

        render_all()

        # we need to flush the console to actually print any changes we make
        libtcod.console_flush()

        for object in objects:
                object.clear()

        # we flush to the console and do all our rendering before handling input
        # in a turn based game, otherwise the initial screen would be blank.

        player_action = handle_keys()
        if player_action == 'exit':
                break

        # for now, monsters wait until the player is done to take their turn
        if game_state == 'playing' and player_action != 'didnt-take-turn':
                for object in objects:
                        if object.ai:
                                object.ai.take_turn()
