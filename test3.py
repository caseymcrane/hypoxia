import libtcodpy as libtcod
import math
import textwrap

#size of the actual libtcod console.
#all sizes are in ascii characters
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

#the width of the status bar, which we currently don't use for anything
BAR_WIDTH = 20

#this is the height of the "panel" console, a separate libtcod console
#that we blit onto the screen on top of the main panel, which contains
#the message log and other GUI elements. note that PANEL_HEIGHT + MAP_HEIGHT = SCREEN_HEIGHT
#at some point we can define this more implicitly when we put more work into the GUI
PANEL_HEIGHT = 7
#the y coordinate offset of the panel. we need this to know where to start drawing text and other things
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT

#these consts define some parameters for the message box
MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1

#inventory panel parameters
INVENTORY_WIDTH = 50

#these define the size of the generated map.
#right now, this is smaller than the screen size, but if we implemented
#a scrolling camera system or something like that, this could be as big as we want
MAP_WIDTH = 80
MAP_HEIGHT = 43

#these are the lower and upper bounds on width and height for room generation
ROOM_MIN_SIZE = 6
ROOM_MAX_SIZE = 10
#the maximum number of rooms the mapgen algorithm will make
MAX_ROOMS = 30
#the upper bounds on items and monsters that mapgen will place.
#currently monsters are only placed in rooms, never in hallways.
MAX_ROOM_ITEMS = 2
MAX_ROOM_MONSTERS = 3

#this determines the algorithm that libtcod uses to calculate the fov_map
#libtcod does all this internally, so we just have to tell it what kind of
#algorithm to use, and specify some other parameters, like whether or not walls
#should be illuminated too, or just floors.
FOV_ALGO = 0
FOV_LIGHT_WALLS = True
#this is the radius that light is projected
#i'd like for this to be dependent on eyes instead of just being a const
TORCH_RADIUS = 10

#we want to limit the FPS pretty low to stop shit from going completely crazy
LIMIT_FPS = 20

#this list is the remnant of an aborted attempt to make an animation for severed limbs flying off
#FLYING_LIMB = ['<','^','>','v','<','^','>','v']

#this block defines the colors for dark floors/walls and lit floors/walls
#i'd like to replace this with some kind of smooth falloff
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
        def __init__(self,x,y,char,name,color,blocks=False,body=None,item=None, death_function = None):
                self.name = name
                self.blocks = blocks
                self.x = x
                self.y = y
                self.char = char
                self.color = color

				#this looks really weird but we need to do this so we can kind of trace back up the tree
				#i.e. if we have a limb, we can find the body that owns it, and then we can find the object that owns the body
                self.body = body
                if self.body:
                        self.body.owner = self

                self.item = item
                if self.item:
                        self.item.owner = self

		'''
		this moves the object by a certain number of tiles
		it's almost always used to just incrementally move in one direction,
		and it shouldn't be used to "teleport" and object to an arbitrary location
		'''
        def move(self,dx,dy):
                if not is_blocked(self.x+dx,self.y+dy):
                        self.x += dx
                        self.y += dy

		'''
		this function moves towards a pair of target coords, one tile at a time
		'''
        def move_towards(self,target_x,target_y):
                dx = target_x - self.x
                dy = target_y - self.y
                #i'd like to try to find a way to not take sqrt
                dist = math.sqrt(dx ** 2 + dy ** 2)

                dx=int(round(dx/dist))
                dy=int(round(dy/dist))

                self.move(dx,dy)

		'''
		UNFINISHED
		this is an implementation of A* pathfinding for bad guys.
		depending on what we set the target to, we can have them make a beeline for the player,
		take cover out of sight, or do anything else. this is a very fast and versatile algo
		UNFINISHED
		
        def move_astar(self,target):
                libtcod.map_new(MAP_WIDTH,MAP_HEIGHT)
                for y1 in range(MAP_HEIGHT):
                        for x1 in range(MAP_WIDTH):
                                libtcod.map_set_properties(fov, x1, y1, not map[x1][y1].block_sight, not map[x1][y1].blocked)
                                
				for obj in objects:
					if obj.blocks and obj!=self and obj!=target:
						libtcod.map_set_properties(fov,obj.x,obj.y,True,False)
                                
                                #ASTAR TUTORIAL         
        ''' 
                                
		def distance_to(self, other):
				dx = other.x - self.x
				dy = other.y - self.y
                return math.sqrt(dx ** 2 + dy ** 2)

		'''
		this sends an object to the back of the objects list, so that it won't overlap other stuff.
		i'd like to replace this with a more robust z layering system, where objects can have a layer
		and layer 0 is drawn first, then layer 1 on top, etc.
		'''
        def send_to_back(self):
                global objects;
                objects.remove(self)
                objects.insert(0,self)

		'''
		this is where the object handles its rendering. right now it's as simple as just placing its
		char at its location
		'''
        def draw(self):
                #the object basically handles its own rendering here
                libtcod.console_set_default_foreground(con,self.color)
                libtcod.console_put_char(con,self.x,self.y,self.char,libtcod.BKGND_NONE)

		'''
		cleanup is messy right now. currently this just has the object blank itself out so it's invisible,
		but it's not actually removed from the objects list in this function. it'd be nice to have it be all one clean routine
		'''
        def clear(self):
                #handle the deletion and cleanup routine. for now just replace with whitespace
                libtcod.console_put_char(con,self.x,self.y,' ',libtcod.BKGND_NONE)

##############################################################################################
#       COMPONENT DEFINITIONS
#############################################################################################

'''
the body class is basically the heart of how the entire combat system works. it could potentially be overhauled
or refactored into part of the object class, but it seems to be fine as it is now, even if some of the
player.body.limb and limb.owner.organs stuff is a little unwieldy.

basically the way it works is that body is just an abstract container for limbs, organs, blood, and your inventory
it doesn't actually have a position, a char, a color, or any of that stuff. it derives all that stuff from the object
it's attached to, so if you instantiate a body without tying it to an object, it's just kind of an abstract clump of data

the body doesn't even have hp. all of that is delegated to the limbs. one possible change could be giving the body a bool
to determine if it's alive or dead, which could be useful as the way we deal with death evolves.
'''
class Body:
        def __init__(self,limbs=[],organs=[],inventory=[],blood=None):
                self.limbs = limbs
                self.organs = organs
                self.inventory = inventory
                self.blood = blood
                
                #take ownership of all the limbs in our limb list
                if len(limbs):
                        for l in limbs:
                                l.owner = self
                                        
                #take ownership of all organs in our organ list.
                #note that currently we don't actually need a heart or a brain or anything to live                        
                if len(organs):
                        for o in organs:
                                o.owner = self
                
        '''
        since the body has no hp and is, in fact, completely abstract, we leave the taking of damage
        to the discretion of individual limbs. right now we choose a limb at random to deal damage to, 
        with a bias toward the torso. later on you'll be able to choose what part of their body to hit
        and with what, dwarf fortress style
        '''
        def take_damage(self,damage):
                if damage > 0:
                        if libtcod.random_get_int(0,0,10)<7:
                                self.limbs[0].take_damage(damage)
                                return self.limbs[0]
                        else:
                                rng_limb = libtcod.random_get_int(0,1,5)
                                self.limbs[rng_limb].take_damage(damage)
                                return self.limbs[rng_limb]
                                
        '''
        this used to be a weird player-specific global function, but i moved it here because that was
        stupid as fuck. it's still a little janky and as our combat system evolves, this might end up
        completely deprecated, but it's adequate for roguelike bump attacking for now.
        '''
        def move_or_attack(self,dx,dy):

                # coords the player is moving/attacking towards
                x = self.owner.x + dx
                y = self.owner.y + dy

                # try to find an attackable object (i.e. one with a body)
                target = None
                for object in objects:
						#is there an object where we're attacking, and does it have a body?
                        if object.body and object.x == x and object.y == y:
                                target = object
                                break

                # attack if you found a target, otherwise move
                if target is not None:
						#so right now this sucks. the way it works is it just goes through your limbs,
						#finds the first one with an attack function, and attacks.
                        for limb in self.limbs:
                                if limb.attack_function is not None:
                                        limb.attack_function(limb, self.owner, target)
                                        break
                
                #hopefully this little else statement will stop you from immediately trampling body of the enemy you just killed
                else:
					self.owner.move(dx,dy)
                                
'''
this is where all the magic happens, as far as combat is concerned. as you can see, it's a very janky proof-of-concept, 
but it mainly works. the constructor is a nightmare but almost all of these properties are optional. below i'll go through 
what they each mean.

hp				the amount of damage this limb can take before its death function is called

name			the name of this limb for both combat log purposes, and severed leg on the ground purposes

strength		how "strong" this limb is. this can be used for a few things, from calculating damage in an attack function to
				determining carrying weight or how easy it is for you to pick up large objects. i.e. it's not just for arms
			
speed			how "fast" this limb is. right now this does absolutely nothing, but i'd like it to determine how fast you can
				move, or how quickly you can deliver a jab or an attack or something
			
organs			these are the parts inside limbs that do stuff. basically, when a limb takes damage, based on the strength of the attack
				and some RNG, the organ(s) can take damage as well. organs are good for you and do important stuff in your body, and if they're
				badly damaged or destroyed, you'll have bigger problems. the main goal is to make hp loss a less linear measure of your health.
				hp represents the absolute limit of what your body parts can take before they are absolutely destroyed, but organ damage will
				be the real killer. organs will comprise obvious things like heart, lungs, brain, etc. but also things like bones. your arm could
				have a bone as its organ, and if that bone breaks, your arm's usability will be pretty well compromised
			
grasp			i couldn't think of a better name for this, but this is basically whatever this limb is holding, which can be anything from an item
				or weapon, to maybe a grapple on an enemy's limb
			
equip			this is basically an equipment slot for armor or clothing or something. maybe this could be made a list, but i don't want someone
				wearing like 5 shirts and 4 pants and 18 pairs of socks, dwarf fortress style
			
grab_function	this is the function the limb will use to grab stuff, both in the sense of picking up items and grappling and anything else.
				it's how an object makes its way into the grasp variable
				
attack_function	this is the function the limb will use to deal damage

take_damage		this dictates how the limb will take damage, how it might proliferate down to the organ level, etc

death_function	this is what happens when you completely lose limb hp, and represents catastrophic structural failure. 
				this is an arm that has been severed or pulverized, a collapsed ribcage, or a caved in skull.
'''
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
                
                #if we have organs, take ownership of them
                if len(organs):
                        for o in organs:
                                o.owner = self.owner
                                        
        def take_damage(self,damage):
                if damage > 0:
                        self.hp -= damage
                if self.hp <= 0:
                        function = self.death_function
                        if function is not None:
                                function(self.owner)

        
##############################################################################################
##################                      LIMB COMPONENT FUNCTIONS

'''
this function does nothing at the moment, but i'm keeping it here as a reminder that eventually you should be able to grab stuff
'''                                
def grab(self,obj):
        if self.strength > obj.weight:
                self.grasp = obj

'''
it's weird passing attacker as an argument, but this is the easiest way i've found to have our messages read "x attacks y's left arm"
instead of "x's left arm attcks y's torso", which just reads weird.

this whole function is pretty placeholder and is mainly there to test that combat kinda works. for example, damage is a constant number
where really i'd rather it either be a random range or a dice roll
'''                        
def attack(self, attacker, target):
        if target.body is not None:
                if self.grasp is not None:
                        limb = target.body.take_damage(self.strength*self.grasp.force_mult+self.grasp.damage)
                        message(attacker.name + ' attacks ' + limb.name + ' with the ' + attacker.grasp.name + ' for ' + str(self.strength*self.grasp.force_mult+self.grasp.damage) + ' damage!')
                else:
                        limb = target.body.take_damage(self.strength)
                        message(attacker.name + ' opens a can of whoopass on ' + limb.name + ' for ' + str(self.strength) + ' damage!', libtcod.red)
                        message('DEBUG ' + limb.name + ": " + str(limb.hp) + ' out of ' + str(limb.max_hp),libtcod.yellow)
                        
                        
##############################################################################################
##################                      LIMB DEATH FUNCTIONS

'''
this is a really shitty death function, and should be replaced ASAP with better stuff. right now, if any of your limbs loses all health,
this guy gets called and basically just turns the enemy into mush. this was only written to check that death_function works properly,
and it is TRASH
'''
def dummydeath(monster):
        monster.owner.char = '%'
        monster.owner.color = libtcod.dark_red
        monster.owner.blocks = False
        monster.owner.name = 'mangled corpse of a ' + monster.owner.name
        monster.owner.send_to_back()
        monster.owner.body = None

                                
##############################################################################################
##############                                          ORGANS

'''
this doesn't really work perfectly right now, but the idea is that enemies have brains, and their brain determines both
the pathfinding they'll use to get to you, and the general kind of approach they'll take with you, determined by strategy
and balanced by fear.

my ultimate idea is to have every actor make a threat and friendliness assessment of every other actor they see, basically sizing them up and
storing that information, maybe updating it if you pull a weapon or something. their strategy and mindset then dictate what they
do with that once they enter combat. if they're more of a timid type, they might find a friendly with the biggest threat and hide behind them.
maybe some people prey on the weak, and will try to take out low-threat stragglers, and maybe others go straight for the biggest guy in the room
'''                                
class Brain:
        def __init__(self,name,hp,iq=None,fear=None,algo=None,strategy=None):
                self.name = name
                self.max_hp = hp
                self.hp = hp
                self.iq = iq
                self.algo = algo
                self.strategy = strategy
                self.fear = fear
                
        '''
        this function is called every time you make a move. hypoxia actually runs in real time, at 20fps, but you wouldn't know it, because
        the AI only takes a turn when you do.
        '''
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

'''
this is totally unfinished, and is really more of a sketch of an idea than anything else.
the general idea was that your heart would beat and would slowly restore health to your limbs,
but that no longer makes sense. instead, it should probably integrate with the blood system, and
basically act as a bullseye for piercing torso attacks. i'm not even going to document the member functions
because they're all trash and will be completely replaced
'''
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
'''
the big idea here is that this'll determine how far you can see, if you can see through walls like thermal vision or something, etc.
right now, like all organs, they don't really do anything.
'''
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

'''
this is also unfinished, but the idea is that if you lose too much blood volume you can pass out and die, and
hard vacuum exposure is gonna mess with your blood pressure and give you ebullism or something. this'll make
more sense once the pressure system is better defined.
'''
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

'''
this was my first attempt at writing a helper function to create people. it's very quick and dirty.
due to the limb and organ system, creating and equipping a person requires quite a bit of legwork.
you have to instantiate all your organs and limbs, connect them all together, connect them to a body,
then create an object that's connected to that body.

pretty soon this should be scrapped in favor of a series of helper functions that can build this stuff up
in useful chunks. making a "standard" human should be pretty easy to do.
'''
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

'''
much like body, this is another sort of container. it only works when tied to an object, but it basically
contains some kind of use function that's applied when you use the item from your inventory. that function is
arbitrary and could do basically anything.
'''
class Item:     
        def __init__(self, use_function=None):
                self.use_function = use_function

		'''
		we're using this pick_up function instead of the grab_function we described earlier for limbs because
		it's simply not ready yet and this was an easier way to check that our inventory system works.
		'''
        def pick_up(self, player):
                
                #we limit inventory size to 26 because we're using letters to index them right now. maybe we
                #can add scrolling selection or something soon
                if len(player.body.inventory) >= 26:
                        message('Your inventory is too full to pick up ' + self.owner.name + '.', libtcod.red)
                else:
                        player.body.inventory.append(self.owner)
                        objects.remove(self.owner)
                        message('You found a ' + self.owner.name + '.', libtcod.green)

		'''
		this calls the item's use function (if it has one) and then deletes the item. this assumes the item is consumable
		'''					
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
                        if libtcod.random_get_int(0,0,100) < 20:
                                break
                        else:

                                monster = create_human_at_pos(x,y,'F',libtcod.blue,'White Castle',8,90,90)

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

        '''
        showing riley how github works
        '''

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
        return names.title()#changes from .capitalize() to .title() 

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
        #put the second condition of this if statement so that items and monsters don't
        #generate until in fov
        for object in objects:
                if object != player and libtcod.map_is_in_fov(fov_map,object.x,object.y):
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

player = create_human_at_pos(0,0,'@',libtcod.red,'Stone Cold E.T.',20,20,200)
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


