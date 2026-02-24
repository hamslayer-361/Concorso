import pygame
import sys
import random
import math

# Initialise Pygame
pygame.init()

# Screen and Tile Settings
width = 1000
height = 800
tileSize = 15
WIN = pygame.display.set_mode((width, height), pygame.RESIZABLE)
pygame.display.set_caption("sprint 2")

# Colour Definitions
black = (0, 0, 0)
wallColour = (10, 0, 0)
floorColour = (140, 100, 0)

# Map Dimensions
mapWidth = width // tileSize
mapHeight = height // tileSize

# Tile Types
wall = 1
floor = 0

# Dungeon Map
dungeonMap = [[wall for _ in range(mapWidth)] for _ in range(mapHeight)]

# Room Settings
roomMinSize = 5
roomMaxSize = 10
corridorWidth = 3

# Global Variables
rooms = []
allItems = []
gameOver = False
totalTreasure = 0
numTotalItems = 0
treasureValue = 0


mapGenerationNeeded = True

# Instead of loading images from files, create simple surfaces for testing
def create_dummy_surface(color):
    surface = pygame.Surface((32, 32))
    surface.fill(color)
    return surface

player_image = create_dummy_surface((0, 255, 0))
weapon_image = create_dummy_surface((255, 0, 0))
treasure_image = create_dummy_surface((255, 255, 0))
monster_image = create_dummy_surface((255, 0, 255))
potion_image = create_dummy_surface((0, 0, 255))


# ---------------------------------------------------------------------
# BSP Node for dungeon partitioning
class BSPNode:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.left = None
        self.right = None
        self.room = None

    def split(self):
        if self.left or self.right:
            return False
        splitHorizontally = self.h / self.w >= 1.25 if self.w / self.h < 1.25 else random.choice([True, False])
        if splitHorizontally:
            maxSplit = self.h - roomMinSize * 2
            if maxSplit < roomMinSize:
                return False
            split = random.randint(roomMinSize, self.h - roomMinSize)
            self.left = BSPNode(self.x, self.y, self.w, split)
            self.right = BSPNode(self.x, self.y + split, self.w, self.h - split)
        else:
            maxSplit = self.w - roomMinSize * 2
            if maxSplit < roomMinSize:
                return False
            split = random.randint(roomMinSize, self.w - roomMinSize)
            self.left = BSPNode(self.x, self.y, split, self.h)
            self.right = BSPNode(self.x + split, self.y, self.w - split, self.h)
        return True

    def create_room(self):
        maxRoomW, maxRoomH = self.w - 2, self.h - 2
        if maxRoomW < roomMinSize or maxRoomH < roomMinSize:
            return
        room_w = random.randint(roomMinSize, min(roomMaxSize, maxRoomW))
        room_h = random.randint(roomMinSize, min(roomMaxSize, maxRoomH))
        room_x = random.randint(self.x + 1, self.x + self.w - room_w - 1)
        room_y = random.randint(self.y + 1, self.y + self.h - room_h - 1)
        candidate = Room(room_x, room_y, room_w, room_h)
        self.room = candidate
        rooms.append(self.room)


# ---------------------------------------------------------------------
# Revised Room class (same as before)
class Room:
    def __init__(self, x, y, width, height):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height
        self.center = ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)
        self.monsters = pygame.sprite.Group()
        self.items = pygame.sprite.Group()

    def intersect(self, other):
        return self.x1 <= other.x2 and self.x2 >= other.x1 and self.y1 <= other.y2 and self.y2 >= other.y1

    def generateContents(self):
        global allItems
        numMonsters = random.randint(0, 2)
        numItems = random.randint(0, 3)
        tiles = [(x, y) for x in range(self.x1 + 1, self.x2 - 1) for y in range(self.y1 + 1, self.y2 - 1)]
        randomTiles = random.sample(tiles, len(tiles))
        for tile in randomTiles:
            x, y = tile
            screen_x, screen_y = x * tileSize, y * tileSize
            if numMonsters > 0:
                self.monsters.add(Monster((screen_x, screen_y), monsterHealthDisplay))
                numMonsters -= 1
                continue
            if numItems > 0:
                itemType = random.choice(['treasure', 'weapon', 'potion'])
                item = Treasure((screen_x, screen_y)) if itemType == 'treasure' else Weapon((screen_x, screen_y)) if itemType == 'weapon' else Potion((screen_x, screen_y))
                self.items.add(item)
                allItems.append(item)
                numItems -= 1
                continue

# ---------------------------------------------------------------------
# Functions to carve rooms and corridors into the dungeon map
def carveRoom(room):
    for x in range(room.x1, room.x2):
        for y in range(room.y1, room.y2):
            dungeonMap[y][x] = floor

def carveHorizontalCorridor(x1, x2, y):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        for i in range(corridorWidth):
            ty = y + i
            if 0 <= ty < mapHeight and 0 <= x < mapWidth:
                dungeonMap[ty][x] = floor

def carveVerticalCorridor(y1, y2, x):
    for y in range(min(y1, y2), max(y1, y2) + 1):
        for i in range(corridorWidth):
            tx = x + i
            if 0 <= y < mapHeight and 0 <= tx < mapWidth:
                dungeonMap[y][tx] = floor

def connectRooms(room1, room2):
    x1, y1 = room1.center
    x2, y2 = room2.center
    if random.choice([True, False]):
        carveHorizontalCorridor(x1, x2, y1)
        carveVerticalCorridor(y1, y2, x2)
    else:
        carveVerticalCorridor(y1, y2, x1)
        carveHorizontalCorridor(x1, x2, y2)

# ---------------------------------------------------------------------
# Helper function to check if a pixel position is walkable (i.e. not a wall)
def isWalkable(x, y):
    tile_x, tile_y = x // tileSize, y // tileSize
    return 0 <= tile_y < mapHeight and 0 <= tile_x < mapWidth and dungeonMap[tile_y][tile_x] != wall

# ---------------------------------------------------------------------
# Create dungeon using BSP algorithm
def createDungeonBSP():
    global dungeonMap, rooms, numTotalItems, treasureDisplay, monsterHealthDisplay, allSprites
    dungeonMap = [[wall for _ in range(mapWidth)] for _ in range(mapHeight)]
    rooms.clear()
    allItems.clear()
    root = BSPNode(0, 0, mapWidth, mapHeight)
    nodes = [root]
    for _ in range(5):  # Split iterations
        newNodes = []
        for node in nodes:
            if node.split():
                newNodes.extend([node.left, node.right])
            else:
                newNodes.append(node)
        nodes = newNodes
    for node in [n for n in nodes if not n.left and not n.right]:
        node.create_room()
        if node.room:
            carveRoom(node.room)
    for i in range(1, len(rooms)):
        connectRooms(rooms[i - 1], rooms[i])
    player = Player((rooms[0].center[0] * tileSize, rooms[0].center[1] * tileSize))
    allSprites = pygame.sprite.Group()
    for room in rooms:
        room.generateContents()
    numTotalItems = len(allItems)
    return player, treasureDisplay, monsterHealthDisplay, allSprites

# Game Entity Classes
class Player(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        original_image = player_image.convert_alpha()
        self.image = pygame.transform.scale(original_image, (32, 32))
        self.rect = self.image.get_rect(topleft=pos)
        self.health = 100
        self.base_damage = 1
        self.inventory = []
        self.move_speed = 2

    def quaff_potion(self):
        if 'potion' in self.inventory:
            self.health = min(self.health + 10, 100)
            self.inventory.remove('potion')
            print("Quaffed a potion! Health:", self.health)

    def attack_damage(self, weapon_count):
        return self.base_damage + (0.5 * weapon_count)

    def handle_keys(self, keys):
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]:
            dx = -self.move_speed
            if isWalkable(self.rect.left + dx, self.rect.top):
                self.rect.x += dx
        if keys[pygame.K_RIGHT]:
            dx = self.move_speed
            if isWalkable(self.rect.right + dx - 1, self.rect.top):
                self.rect.x += dx
        if keys[pygame.K_UP]:
            dy = -self.move_speed
            if isWalkable(self.rect.left, self.rect.top + dy):
                self.rect.y += dy
        if keys[pygame.K_DOWN]:
            dy = self.move_speed
            if isWalkable(self.rect.left, self.rect.bottom + dy - 1):
                self.rect.y += dy
        if keys[pygame.K_q]:
            self.quaff_potion()

    def handle_attack(self, keys, current_room):
        if keys[pygame.K_SPACE]:
            for monster in current_room.monsters:
                if pygame.sprite.collide_rect(self, monster):
                    weapon_count = sum(
                        1 for item in current_room.items if hasattr(item, 'type') and item.type == 'weapon'
                    )
                    damage = self.attack_damage(weapon_count)
                    monster.take_damage(damage)

    def update(self):
        pass

class Weapon(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = pygame.transform.scale(weapon_image, (32, 32))
        self.rect = self.image.get_rect(topleft=pos)
        self.type = 'weapon'

class Treasure(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        original_image = treasure_image.convert_alpha()
        self.image = pygame.transform.scale(original_image, (32, 32))
        self.rect = self.image.get_rect(topleft=pos)
        self.type = 'treasure'

class Potion(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        original_image = potion_image.convert_alpha()
        self.image = pygame.transform.scale(original_image, (32, 32))
        self.rect = self.image.get_rect(topleft=pos)
        self.type = 'potion'

class Monster(pygame.sprite.Sprite):
    def __init__(self, pos, health_display):
        super().__init__()
        self.health = 50
        self.health_display = health_display
        original_image = monster_image.convert_alpha()
        self.image = pygame.transform.scale(original_image, (32, 32))
        self.rect = self.image.get_rect(topleft=pos)
        self.hit_animation_timer = 0
        self.speed = 1  # Movement speed for chasing

    def chase(self, target):
        # Calculate vector towards the target (player)
        dx = target.rect.centerx - self.rect.centerx
        dy = target.rect.centery - self.rect.centery
        distance = math.hypot(dx, dy)
        if distance > 0:
            dx /= distance
            dy /= distance
        # Move the monster a step towards the player
        self.rect.x += int(dx * self.speed)
        self.rect.y += int(dy * self.speed)

    def take_damage(self, damage):
        self.health_display.update_current_monster(self)
        self.health -= damage
        self.hit_animation_timer = 5
        if self.health <= 0:
            self.kill()

    def update(self):
        if self.hit_animation_timer > 0:
            self.hit_animation_timer -= 1

    def draw(self, screen):
        if self.hit_animation_timer > 0:
            oval_rect = self.rect.inflate(20, 40)
            pygame.draw.ellipse(screen, (255, 0, 0), oval_rect)
        screen.blit(self.image, self.rect)


clock = pygame.time.Clock()
FPS = 60

# Create HUD-like dummy objects
class DummyDisplay:
    def update_current_monster(self, monster): pass
    def draw(self, screen): pass

treasureDisplay = DummyDisplay()
monsterHealthDisplay = DummyDisplay()

# Generate dungeon and place player
player, treasureDisplay, monsterHealthDisplay, allSprites = createDungeonBSP()

running = True
while running:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    player.handle_keys(keys)

    # Update all room contents (monsters chase player)
    for room in rooms:
        for monster in room.monsters:
            monster.chase(player)
            monster.update()

    # Handle attacks (spacebar)
    for room in rooms:
        if room.x1 <= player.rect.centerx // tileSize <= room.x2 and room.y1 <= player.rect.centery // tileSize <= room.y2:
            player.handle_attack(keys, room)

    # Drawing
    WIN.fill(black)

    # Draw dungeon map
    for y in range(mapHeight):
        for x in range(mapWidth):
            tile_color = floorColour if dungeonMap[y][x] == floor else wallColour
            pygame.draw.rect(WIN, tile_color, (x * tileSize, y * tileSize, tileSize, tileSize))

    # Draw all items and monsters
    for room in rooms:
        room.items.draw(WIN)
        for monster in room.monsters:
            monster.draw(WIN)

    # Draw player
    WIN.blit(player.image, player.rect)

    pygame.display.flip()

pygame.quit()
sys.exit()
