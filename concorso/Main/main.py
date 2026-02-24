import pygame
import sys
import random
import math
import json
from collections import Counter

# Initialise Pygame
pygame.init()

# Screen and Tile Settings
width = 1000
height = 800
tileSize = 15
WIN = pygame.display.set_mode((width, height), pygame.RESIZABLE)
pygame.display.set_caption("Concorso")

# Colour Definitions
white = (255, 255, 255)
black = (0, 0, 0)
lightBlue = (200, 220, 255)  # Menu backgrounds
wallColour = (10, 0, 0)
floorColour = (140, 100, 0)
red = (255, 0, 0)
green = (0, 255, 0)
gray = (50, 50, 50)
darkGrey = (30, 30, 30)

# UI Panel Forbidden Area
forbiddenWidth = 250
forbiddenHeight = 120
forbiddenWidthTiles = math.ceil(forbiddenWidth / tileSize)  # ~17 tiles
forbiddenHeightTiles = math.ceil(forbiddenHeight / tileSize)  # ~8 tiles

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
currentSeed = random.randint(0, 10 ** 6)
random.seed(currentSeed)

# Menu Flags
saveMenuActive = False
loadMenuActive = False
inventoryMenuActive = False
statMenuActive = False

# Game States
mainMenu = "MAIN_MENU"
classSelect = "CLASS_SELECT"
playing = "PLAYING"
leaderboard = "LEADERBOARD"
GAME_OVER = "GAME_OVER"
store = "STORE"
gameState = mainMenu

# Game Flags
mapGenerationNeeded = True
playerClass = None
classNames = ["Warrior", "Ranger", "Assassin"]

# Button Configurations
buttonWidth = 300
buttonHeight = 60
buttonSpacing = 20

# Main Menu Buttons
startButtonRect = pygame.Rect(width // 2 - buttonWidth // 2, height // 2 - 100, buttonWidth, buttonHeight)
leaderboardButtonRect = pygame.Rect(width // 2 - buttonWidth // 2, height // 2 - 100 + buttonHeight + buttonSpacing, buttonWidth, buttonHeight)
storeButtonRect = pygame.Rect(width // 2 - buttonWidth // 2, height // 2 - 100 + 2 * (buttonHeight + buttonSpacing), buttonWidth, buttonHeight)

# Class Select Buttons
classButtonRects = [pygame.Rect(width // 2 - buttonWidth // 2, height // 2 - 100 + i * (buttonHeight + buttonSpacing), buttonWidth, buttonHeight) for i in range(len(classNames))]

# Leaderboard Button
backButtonRect = pygame.Rect(width // 2 - buttonWidth // 2, height // 2 + 150, buttonWidth, buttonHeight)

# Game Over Button
gameOverButtonWidth = 200
gameOverButtonHeight = 60
gameOverButtonRect = pygame.Rect(width // 2 - gameOverButtonWidth // 2, height // 2 + 50, gameOverButtonWidth, gameOverButtonHeight)

# Store Buttons
storeButtonWidth = 300
storeButtonHeight = 60
storeButtonSpacing = 20
storeOptions = ["Sell item", "Buy item", "Redeem rewards", "Back to main menu"]
storeButtonRects = [pygame.Rect(width // 2 - storeButtonWidth // 2, height // 2 - 100 + i * (storeButtonHeight + storeButtonSpacing), storeButtonWidth, storeButtonHeight) for i in range(len(storeOptions))]

# Font
menuFont = pygame.font.SysFont(None, 36)

# Utility Functions
def create_surface(colour):
    surface = pygame.Surface((32, 32))
    surface.fill(colour)
    return surface

# Image Placeholders
playerImage = create_surface((0, 255, 0))
weaponImage = create_surface((255, 0, 0))
treasureImage = create_surface((255, 255, 0))
monsterImage = create_surface((255, 0, 255))
potionImage = create_surface((0, 0, 255))

# Classes

# BSP Node for Dungeon Partitioning
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
        if candidate.x1 < forbiddenWidthTiles and candidate.y1 < forbiddenHeightTiles:
            return
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

# Player Class
class Player(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = pygame.transform.scale(playerImage.convert_alpha(), (32, 32))
        self.rect = self.image.get_rect(topleft=pos)
        self.health = 100
        self.maxHealth = 100
        self.baseDamage = 1
        self.inventory = []
        self.moveSpeed = 2

    def quaff_potion(self):
        if 'potion' in self.inventory:
            healAmount = int(self.maxHealth * 0.2)
            self.health = min(self.health + healAmount, self.maxHealth)
            self.inventory.remove('potion')
            print("Quaffed a potion! Health:", self.health)
        else:
            print("No potions in inventory!")

    def attackDamage(self):
        return self.baseDamage * (1 + 0.1 * self.inventory.count('weapon'))

    def handleKeys(self, keys):
        dx, dy = 0, 0
        if keys[pygame.K_LEFT] and isWalkable(self.rect.left - self.moveSpeed, self.rect.top):
            dx = -self.moveSpeed
        if keys[pygame.K_RIGHT] and isWalkable(self.rect.right + self.moveSpeed - 1, self.rect.top):
            dx = self.moveSpeed
        if keys[pygame.K_UP] and isWalkable(self.rect.left, self.rect.top - self.moveSpeed):
            dy = -self.moveSpeed
        if keys[pygame.K_DOWN] and isWalkable(self.rect.left, self.rect.bottom + self.moveSpeed - 1):
            dy = self.moveSpeed
        if keys[pygame.K_q]:
            self.quaff_potion()
        self.rect.x += dx
        self.rect.y += dy

    def handleAttack(self, keys, currentRoom):
        if keys[pygame.K_SPACE]:
            for monster in currentRoom.monsters:
                if pygame.sprite.collide_rect(self, monster):
                    monster.take_damage(self.attackDamage())

    def update(self):
        pass

# Weapon Class
class Weapon(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = pygame.transform.scale(weaponImage, (32, 32))
        self.rect = self.image.get_rect(topleft=pos)
        self.type = 'weapon'

# Treasure Class
class Treasure(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = pygame.transform.scale(treasureImage.convert_alpha(), (32, 32))
        self.rect = self.image.get_rect(topleft=pos)
        self.type = 'treasure'

# Potion Class
class Potion(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = pygame.transform.scale(potionImage.convert_alpha(), (32, 32))
        self.rect = self.image.get_rect(topleft=pos)
        self.type = 'potion'

# Monster Class
class Monster(pygame.sprite.Sprite):
    def __init__(self, pos, healthDisplay):
        super().__init__()
        self.health = 50
        self.healthDisplay = healthDisplay
        self.image = pygame.transform.scale(monsterImage.convert_alpha(), (32, 32))
        self.rect = self.image.get_rect(topleft=pos)
        self.hitAnimationTimer = 0
        self.speed = 1

    def chase(self, target):
        dx = target.rect.centerx - self.rect.centerx
        dy = target.rect.centery - self.rect.centery
        distance = math.hypot(dx, dy)
        if distance > 0:
            dx, dy = dx / distance, dy / distance
            self.rect.x += round(dx * self.speed)
            self.rect.y += round(dy * self.speed)

    def take_damage(self, damage):
        self.healthDisplay.updateCurrentMonster(self)
        self.health -= damage
        self.hitAnimationTimer = 5
        if self.health <= 0:
            self.kill()

    def update(self):
        if self.hitAnimationTimer > 0:
            self.hitAnimationTimer -= 1

    def draw(self, screen, cameraOffset):
        if self.hitAnimationTimer > 0:
            pygame.draw.ellipse(screen, red, self.rect.move(-cameraOffset[0], -cameraOffset[1]).inflate(20, 40))
        screen.blit(self.image, (self.rect.x - cameraOffset[0], self.rect.y - cameraOffset[1]))

# Health Display Class
class HealthDisplay(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((200, 50))
        self.image.fill((100, 100, 100))
        self.rect = self.image.get_rect(topleft=(400, 10))
        self.font = pygame.font.SysFont(None, 20)
        self.monster = None

    def updateCurrentMonster(self, monster):
        self.monster = monster
        self.image.fill((100, 100, 100))
        if self.monster and self.monster.health > 1.0:
            healthText = self.font.render(f"Health Value: {self.monster.health}", True, white)
            self.image.blit(healthText, (10, 10))

    def update(self):
        pass

# Treasure Value Display Class
class TreasureValueDisplay(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.updateDisplay()

    def updateDisplay(self):
        global treasureValue
        font = pygame.font.SysFont(None, 24)
        self.image = font.render(f"Treasure Value: {treasureValue}", True, white)
        self.rect = self.image.get_rect(topleft=(200, 10))

    def update(self):
        self.updateDisplay()

# UI Panel Class
class UIPanel:
    def __init__(self, player, treasure_value, inventory, width=250, height=120):
        self.player = player
        self.treasureValue = treasure_value
        self.inventory = inventory
        self.width = width
        self.height = height
        self.panelColour = gray
        self.font = pygame.font.SysFont(None, 24)
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self.healthBarWidth = 150
        self.healthBarHeight = 15
        self.healthBarPosition = (10, 10)
        self.healthBorderColour = white

    def update(self, treasure_value):
        self.treasureValue = treasure_value

    def draw(self, surface):
        pygame.draw.rect(surface, self.panelColour, self.rect)
        health_bar_rect = pygame.Rect(self.healthBarPosition[0], self.healthBarPosition[1], self.healthBarWidth, self.healthBarHeight)
        pygame.draw.rect(surface, self.healthBorderColour, health_bar_rect, 2)
        fillWidth = int((self.player.health / self.player.maxHealth) * (self.healthBarWidth - 4))
        pygame.draw.rect(surface, green, (self.healthBarPosition[0] + 2, self.healthBarPosition[1] + 2, fillWidth, self.healthBarHeight - 4))
        treasureText = self.font.render(f'Treasure: {self.treasureValue}', True, white)
        surface.blit(treasureText, (10, 40))

# Dungeon Generation Functions
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

def carveHorizontal(x_start, x_end, y_coord):
    if y_coord < forbiddenHeightTiles:
        new_y = forbiddenHeightTiles
        carveVerticalCorridor(y_coord, new_y, x_start)
        carveHorizontalCorridor(x_start, x_end, new_y)
        carveVerticalCorridor(new_y, y_coord, x_end)
    else:
        carveHorizontalCorridor(x_start, x_end, y_coord)

def carveVertical(y_start, y_end, x_coord):
    if x_coord < forbiddenWidthTiles:
        new_x = forbiddenWidthTiles
        carveHorizontalCorridor(x_coord, new_x, y_start)
        carveVerticalCorridor(y_start, y_end, new_x)
        carveHorizontalCorridor(new_x, x_coord, y_end)
    else:
        carveVerticalCorridor(y_start, y_end, x_coord)

def connectRooms(room1, room2):
    x1, y1 = room1.center
    x2, y2 = room2.center
    if random.choice([True, False]):
        carveHorizontal(x1, x2, y1)
        carveVertical(y1, y2, x2)
    else:
        carveVertical(y1, y2, x1)
        carveHorizontal(x1, x2, y2)

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
    treasureDisplay = TreasureValueDisplay()
    monsterHealthDisplay = HealthDisplay()
    allSprites = pygame.sprite.Group(treasureDisplay, monsterHealthDisplay)
    for room in rooms:
        room.generateContents()
    numTotalItems = len(allItems)
    return player, treasureDisplay, monsterHealthDisplay, allSprites

#Save/Load Functions
def saveGameSlot(player, slot):
    data = {
        'seed': currentSeed,
        'player': {'x': player.rect.x, 'y': player.rect.y, 'health': player.health, 'inventory': player.inventory},
        'treasure_value': treasureValue
    }
    with open(f"savegame_slot{slot}.json", "w") as f:
        json.dump(data, f)
    print(f"Game saved in slot {slot}.")

def loadGameSlot(slot):
    global player, treasureValue, rooms, dungeonMap, allItems, treasureDisplay, monsterHealthDisplay, allSprites, ui_panel, currentSeed
    try:
        with open(f"savegame_slot{slot}.json", "r") as f:
            data = json.load(f)
    except Exception as e:
        print("Failed to load game:", e)
        return
    currentSeed = data['seed']
    random.seed(currentSeed)
    player, treasureDisplay, monsterHealthDisplay, allSprites = createDungeonBSP()
    player.rect.x, player.rect.y = data['player']['x'], data['player']['y']
    player.health, player.inventory = data['player']['health'], data['player']['inventory']
    treasureValue = data['treasure_value']
    ui_panel = UIPanel(player, treasureValue, player.inventory)
    WIN.fill(black)
    pygame.display.flip()
    pygame.time.delay(10)
    print(f"Game loaded from slot {slot}.")

# Helper Function
def isWalkable(x, y):
    tile_x, tile_y = x // tileSize, y // tileSize
    return 0 <= tile_y < mapHeight and 0 <= tile_x < mapWidth and dungeonMap[tile_y][tile_x] != wall

# Menu Functions

# Stat Menu
def drawStatMenu():
    overlay = pygame.Surface((width, height))
    overlay.set_alpha(200)
    overlay.fill(darkGrey)
    WIN.blit(overlay, (0, 0))
    statFont = pygame.font.SysFont(None, 36)
    maxHealthText = statFont.render(f"Max Health: {player.maxHealth}", True, white)
    attackBonus = player.inventory.count("weapon") * 10
    attackText = statFont.render(f"Attack Bonus: {attackBonus}%", True, white)
    instructionText = statFont.render("Press ESC to close", True, white)
    WIN.blit(maxHealthText, (width // 2 - maxHealthText.get_width() // 2, height // 2 - 100))
    WIN.blit(attackText, (width // 2 - attackText.get_width() // 2, height // 2 - 50))
    WIN.blit(instructionText, (width // 2 - instructionText.get_width() // 2, height // 2 + 50))

def handleStatMenuEvents(event):
    global statMenuActive
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        statMenuActive = False

# Store Menu
def drawStoreMenu():
    WIN.fill(lightBlue)
    titleFont = pygame.font.SysFont(None, 50)
    titleText = titleFont.render("Virtual Store", True, black)
    WIN.blit(titleText, (width // 2 - titleText.get_width() // 2, 100))
    for i, rect in enumerate(storeButtonRects):
        pygame.draw.rect(WIN, black, rect)
        optionSurf = menuFont.render(storeOptions[i], True, white)
        WIN.blit(optionSurf, (rect.centerx - optionSurf.get_width() // 2, rect.centery - optionSurf.get_height() // 2))

def handleStoreMenuEvents(event):
    global gameState, mapGenerationNeeded
    if event.type == pygame.MOUSEBUTTONDOWN:
        mx, my = event.pos
        for i, rect in enumerate(storeButtonRects):
            if rect.collidepoint(mx, my):
                if i == 0:
                    print("Sell item clicked!")
                elif i == 1:
                    print("Buy item clicked!")
                elif i == 2:
                    print("Redeem rewards clicked!")
                elif i == 3:
                    print("Back to main menu clicked!")
                    gameState = mainMenu
                    mapGenerationNeeded = True

# Main Menu
def drawMainMenu():
    WIN.fill(lightBlue)
    title_font = pygame.font.SysFont(None, 60)
    title_text = title_font.render("Concorso", True, black)
    WIN.blit(title_text, (width // 2 - title_text.get_width() // 2, 100))
    pygame.draw.rect(WIN, black, startButtonRect)
    pygame.draw.rect(WIN, black, leaderboardButtonRect)
    pygame.draw.rect(WIN, black, storeButtonRect)
    btn_font = pygame.font.SysFont(None, 36)
    start_text = btn_font.render("Start Game", True, white)
    lb_text = btn_font.render("Leaderboard", True, white)
    store_text = btn_font.render("Virtual Store", True, white)
    WIN.blit(start_text, (startButtonRect.centerx - start_text.get_width() // 2, startButtonRect.centery - start_text.get_height() // 2))
    WIN.blit(lb_text, (leaderboardButtonRect.centerx - lb_text.get_width() // 2, leaderboardButtonRect.centery - lb_text.get_height() // 2))
    WIN.blit(store_text, (storeButtonRect.centerx - store_text.get_width() // 2, storeButtonRect.centery - store_text.get_height() // 2))

def handleMainMenuEvents(event):
    global gameState, mapGenerationNeeded
    if event.type == pygame.MOUSEBUTTONDOWN:
        mx, my = event.pos
        if startButtonRect.collidepoint(mx, my):
            print("Start Game clicked!")
            gameState = classSelect
            mapGenerationNeeded = True
        elif leaderboardButtonRect.collidepoint(mx, my):
            print("Leaderboard clicked!")
            gameState = leaderboard
            mapGenerationNeeded = True
        elif storeButtonRect.collidepoint(mx, my):
            print("Virtual Store clicked!")
            gameState = store
            mapGenerationNeeded = True

# Class Select Menu
def drawClassMenu():
    WIN.fill(lightBlue)
    title_font = pygame.font.SysFont(None, 50)
    title_text = title_font.render("Select Your Class", True, black)
    WIN.blit(title_text, (width // 2 - title_text.get_width() // 2, 100))
    btn_font = pygame.font.SysFont(None, 36)
    for i, cname in enumerate(classNames):
        rect = classButtonRects[i]
        pygame.draw.rect(WIN, black, rect)
        text_surf = btn_font.render(cname, True, white)
        WIN.blit(text_surf, (rect.centerx - text_surf.get_width() // 2, rect.centery - text_surf.get_height() // 2))

def handleClassMenuEvents(event):
    global gameState, playerClass, player
    if event.type == pygame.MOUSEBUTTONDOWN:
        mx, my = event.pos
        for i, rect in enumerate(classButtonRects):
            if rect.collidepoint(mx, my):
                playerClass = classNames[i]
                print(f"Class chosen: {playerClass}")
                if playerClass == "Warrior":
                    player.maxHealth = player.health = 150
                elif playerClass == "Ranger":
                    player.inventory.extend(["weapon"] * 2)
                elif playerClass == "Assassin":
                    player.moveSpeed = int(player.moveSpeed * 1.3)
                    player.inventory.append("weapon")
                WIN.fill(black)
                pygame.display.flip()
                pygame.time.delay(10)
                gameState = playing

# Leaderboard
def drawLeaderboard():
    WIN.fill(lightBlue)
    titleFont = pygame.font.SysFont(None, 50)
    titleText = titleFont.render("Leaderboard", True, black)
    WIN.blit(titleText, (width // 2 - titleText.get_width() // 2, 100))
    table_x, table_y, tableWidth, tableHeight = width // 2 - 200, height // 2 - 100, 400, 200
    pygame.draw.rect(WIN, black, (table_x, table_y, tableWidth, tableHeight), 2)
    colWidth = tableWidth // 3
    for i in range(1, 3):
        pygame.draw.line(WIN, black, (table_x + i * colWidth, table_y), (table_x + i * colWidth, table_y + tableHeight), 2)
    headerHeight = 40
    pygame.draw.line(WIN, black, (table_x, table_y + headerHeight), (table_x + tableWidth, table_y + headerHeight), 2)
    headerFont = pygame.font.SysFont(None, 28)
    for text, x in [("Name", table_x + colWidth // 2), ("Level", table_x + colWidth + colWidth // 2), ("Time", table_x + 2 * colWidth + colWidth // 2)]:
        rendered = headerFont.render(text, True, black)
        WIN.blit(rendered, (x - rendered.get_width() // 2, table_y + headerHeight // 2 - rendered.get_height() // 2))
    pygame.draw.rect(WIN, black, backButtonRect)
    backText = pygame.font.SysFont(None, 36).render("Back to main menu", True, white)
    WIN.blit(backText, (backButtonRect.centerx - backText.get_width() // 2, backButtonRect.centery - backText.get_height() // 2))

def handleLeaderboardEvents(event):
    global gameState, mapGenerationNeeded
    if event.type == pygame.MOUSEBUTTONDOWN and backButtonRect.collidepoint(event.pos):
        print("Returning to main menu...")
        gameState = mainMenu
        mapGenerationNeeded = True

# Game Over Screen
def drawGameOverScreen(score):
    WIN.fill(lightBlue)
    titleText = pygame.font.SysFont(None, 50).render("You have died", True, black)
    scoreText = pygame.font.SysFont(None, 36).render(f"Score: {score}", True, black)
    WIN.blit(titleText, (width // 2 - titleText.get_width() // 2, height // 2 - 150))
    WIN.blit(scoreText, (width // 2 - scoreText.get_width() // 2, height // 2 - 70))
    pygame.draw.rect(WIN, black, gameOverButtonRect)
    backText = pygame.font.SysFont(None, 28).render("Back to main menu", True, white)
    WIN.blit(backText, (gameOverButtonRect.centerx - backText.get_width() // 2, gameOverButtonRect.centery - backText.get_height() // 2))

def handleGameOverEvents(event):
    global gameState, mapGenerationNeeded
    if event.type == pygame.MOUSEBUTTONDOWN and gameOverButtonRect.collidepoint(event.pos):
        gameState = mainMenu
        mapGenerationNeeded = True

# Main Game Loop
clock = pygame.time.Clock()
player, treasureDisplay, monsterHealthDisplay, allSprites = createDungeonBSP()
ui_panel = UIPanel(player, treasureValue, player.inventory)
running = True

while running:
    clock.tick(60)
    if gameState == mainMenu:
        if mapGenerationNeeded:
            player, treasureDisplay, monsterHealthDisplay, allSprites = createDungeonBSP()
            ui_panel = UIPanel(player, treasureValue, player.inventory)
            mapGenerationNeeded = False
        drawMainMenu()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                handleMainMenuEvents(event)
        pygame.display.flip()
    elif gameState == classSelect:
        drawClassMenu()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                handleClassMenuEvents(event)
        pygame.display.flip()
    elif gameState == leaderboard:
        drawLeaderboard()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                handleLeaderboardEvents(event)
        pygame.display.flip()
    elif gameState == store:
        drawStoreMenu()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                handleStoreMenuEvents(event)
        pygame.display.flip()
    elif gameState == GAME_OVER:
        drawGameOverScreen(treasureValue)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                handleGameOverEvents(event)
        pygame.display.flip()
    elif gameState == playing:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif saveMenuActive:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        saveMenuActive = False
                    elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5]:
                        saveGameSlot(player, event.key - pygame.K_0)
                        saveMenuActive = False
            elif loadMenuActive:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        loadMenuActive = False
                    elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5]:
                        loadGameSlot(event.key - pygame.K_0)
                        loadMenuActive = False
            elif inventoryMenuActive:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        inventoryMenuActive = False
                    elif event.key == pygame.K_u:
                        player.quaff_potion()
            elif statMenuActive:
                handleStatMenuEvents(event)
            else:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_s:
                        saveMenuActive = True
                    elif event.key == pygame.K_l:
                        loadMenuActive = True
                    elif event.key == pygame.K_i:
                        inventoryMenuActive = True
                    elif event.key == pygame.K_t:
                        statMenuActive = True
        if not (saveMenuActive or loadMenuActive or inventoryMenuActive or statMenuActive):
            cameraOffset = (player.rect.centerx - width // 2, player.rect.centery - height // 2)
            keys = pygame.key.get_pressed()
            player.handleKeys(keys)
            current_room = next((room for room in rooms if room.x1 <= player.rect.centerx // tileSize <= room.x2 and room.y1 <= player.rect.centery // tileSize <= room.y2), None)
            if current_room:
                player.handleAttack(keys, current_room)
                for monster in current_room.monsters:
                    monster.chase(player)
                for item in pygame.sprite.spritecollide(player, current_room.items, True):
                    player.inventory.append(item.type)
                    if item.type == 'treasure':
                        treasureValue += 1
                        treasureDisplay.updateDisplay()
                    numTotalItems -= 1
                    print('Total items left:', numTotalItems)
                    if numTotalItems <= 0:
                        gameOver = True
                if pygame.sprite.spritecollideany(player, current_room.monsters):
                    player.health -= 0.10
            if player.health <= 0 or gameOver:
                gameState = GAME_OVER
            for y in range(mapHeight):
                for x in range(mapWidth):
                    rect = pygame.Rect(x * tileSize - cameraOffset[0], y * tileSize - cameraOffset[1], tileSize, tileSize)
                    pygame.draw.rect(WIN, wallColour if dungeonMap[y][x] == wall else floorColour, rect)
            if current_room:
                for item in current_room.items:
                    WIN.blit(item.image, (item.rect.x - cameraOffset[0], item.rect.y - cameraOffset[1]))
                current_room.monsters.update()
                for monster in current_room.monsters:
                    monster.draw(WIN, cameraOffset)
            WIN.blit(player.image, (player.rect.x - cameraOffset[0], player.rect.y - cameraOffset[1]))
            ui_panel.update(treasureValue)
            ui_panel.draw(WIN)
            allSprites.draw(WIN)
        else:
            overlay = pygame.Surface((width, height))
            overlay.set_alpha(200)
            overlay.fill(darkGrey)
            WIN.blit(overlay, (0, 0))
            if saveMenuActive:
                menu_text = menuFont.render("Save Game - Choose Slot (1-5)", True, white)
            elif loadMenuActive:
                menu_text = menuFont.render("Load Game - Choose Slot (1-5)", True, white)
            elif inventoryMenuActive:
                menu_text = menuFont.render("Inventory - Press ESC to Close", True, white)
            elif statMenuActive:
                drawStatMenu()
            if not statMenuActive:
                WIN.blit(menu_text, (width // 2 - menu_text.get_width() // 2, height // 2 - 100))
                if inventoryMenuActive:
                    inv_counter = Counter(player.inventory)
                    y_offset = height // 2 - 60
                    if inv_counter:
                        for item, count in inv_counter.items():
                            item_text = menuFont.render(f"{item} x {count}", True, white)
                            WIN.blit(item_text, (width // 2 - item_text.get_width() // 2, y_offset))
                            y_offset += 40
                    else:
                        emptyText = menuFont.render("Inventory Empty", True, white)
                        WIN.blit(emptyText, (width // 2 - emptyText.get_width() // 2, height // 2 - 20))
                    useText = menuFont.render("Press U to use a potion", True, white)
                    WIN.blit(useText, (width // 2 - useText.get_width() // 2, y_offset + 20))
                else:
                    for i in range(1, 6):
                        slot_text = menuFont.render(f"Slot {i}", True, white)
                        WIN.blit(slot_text, (width // 2 - slot_text.get_width() // 2, height // 2 - 60 + i * 40))
                    cancelText = menuFont.render("Press ESC to Cancel", True, white)
                    WIN.blit(cancelText, (width // 2 - cancelText.get_width() // 2, height // 2 + 150))
        pygame.display.flip()

pygame.quit()
sys.exit()