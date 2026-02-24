import pygame
import sys
import random
import math
import json

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

# Room Settings
roomMinSize = 5
roomMaxSize = 10
corridorWidth = 3

# Global variables
rooms = []

# Utility Functions
def createSurface(colour):
    surface = pygame.Surface((32, 32))
    surface.fill(colour)
    return surface

# Image Placeholders
playerImage = createSurface((0, 255, 0))
weaponImage = createSurface((255, 0, 0))
treasureImage = createSurface((255, 255, 0))
monsterImage = createSurface((255, 0, 255))
potionImage = createSurface((0, 0, 255))

# BSP Node for dungeon partitioning
class BSPNode:
    def __init__(self, x, y, w, h):
        self.x = x  # top-left corner x
        self.y = y  # top-left corner y
        self.w = w  # width
        self.h = h  # height
        self.left = None  # left child after split
        self.right = None  # right child after split
        self.room = None  # room that may be placed in this region


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

    def createRoom(self):
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

# Room Class
class Room:
    def __init__(self, x, y, width, height):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height
        self.center = ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    def intersect(self, other):
        return self.x1 <= other.x2 and self.x2 >= other.x1 and self.y1 <= other.y2 and self.y2 >= other.y1


# Game Entity Classes
class Player(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        original_image = playerImage.convert_alpha()
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
        self.image = pygame.transform.scale(weaponImage, (32, 32))
        self.rect = self.image.get_rect(topleft=pos)
        self.type = 'weapon'

class Treasure(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        original_image = treasureImage.convert_alpha()
        self.image = pygame.transform.scale(original_image, (32, 32))
        self.rect = self.image.get_rect(topleft=pos)
        self.type = 'treasure'

class Potion(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        original_image = potionImage.convert_alpha()
        self.image = pygame.transform.scale(original_image, (32, 32))
        self.rect = self.image.get_rect(topleft=pos)
        self.type = 'potion'

class Monster(pygame.sprite.Sprite):
    def __init__(self, pos, health_display):
        super().__init__()
        self.health = 50
        self.health_display = health_display
        original_image = monsterImage.convert_alpha()
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

def create_bsp_tree(root, depth=5):
    nodes = [root]
    for _ in range(depth):
        new_nodes = []
        for node in nodes:
            if node.split():
                new_nodes.append(node.left)
                new_nodes.append(node.right)
        nodes.extend(new_nodes)
    # Only create rooms in leaf nodes
    leaf_nodes = [node for node in nodes if not node.left and not node.right]
    for node in leaf_nodes:
        node.createRoom()

    return nodes


def draw_rooms():
    for room in rooms:
        pygame.draw.rect(WIN,floorColour,pygame.Rect(room.x1 * tileSize, room.y1 * tileSize,(room.x2 - room.x1) * tileSize, (room.y2 - room.y1) * tileSize))


def main():
    clock = pygame.time.Clock()
    running = True

    # Dungeon generation
    root = BSPNode(0, 0, mapWidth, mapHeight)
    create_bsp_tree(root)

    while running:
        WIN.fill(black)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        draw_rooms()

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
