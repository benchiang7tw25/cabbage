import pygame
import random
import sys
import colorsys
import os

# 初始化 Pygame
pygame.init()

# 定義顏色
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)

# 遊戲設置
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
GRID_SIZE = 20
GRID_WIDTH = WINDOW_WIDTH // GRID_SIZE
GRID_HEIGHT = WINDOW_HEIGHT // GRID_SIZE

# 創建遊戲窗口
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption('大頭蛇')

# 初始化 font
try:
    # Try to use a system font that supports Chinese
    title_font = pygame.font.SysFont('microsoftyaheimicrosoftyaheiui', 72)
    font = pygame.font.SysFont('microsoftyaheimicrosoftyaheiui', 36)
except:
    # Fallback to default font if the Chinese font is not available
    title_font = pygame.font.Font(None, 72)
    font = pygame.font.Font(None, 36)

class Snake:
    def __init__(self):
        self.positions = [(GRID_WIDTH // 2, GRID_HEIGHT // 2)]
        self.direction = (1, 0)
        self.length = 1
        self.score = 0
        self.trail = []  # Store trail positions
        self.trail_length = 20  # Length of the trail
        self.mouth_timer = 0  # Timer for mouth animation
        self.lives = 3  # Start with 3 lives

    def get_head_positions(self):
        # Return all 9 positions of the 3x3 head
        head_pos = self.positions[0]
        positions = []
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                positions.append((head_pos[0] + dx, head_pos[1] + dy))
        return positions

    def move(self):
        cur = self.positions[0]
        x, y = self.direction
        new_x = cur[0] + x
        new_y = cur[1] + y
        
        # Check for wall collision and bounce back
        if new_x < 1 or new_x >= GRID_WIDTH - 1:  # Adjusted for 3x3 head
            self.direction = (-x, y)  # Reverse x direction
            new_x = cur[0] + self.direction[0]
        if new_y < 1 or new_y >= GRID_HEIGHT - 1:  # Adjusted for 3x3 head
            self.direction = (x, -y)  # Reverse y direction
            new_y = cur[1] + self.direction[1]
            
        new = (new_x, new_y)
        
        # Check collision with body using all head positions
        head_positions = self.get_head_positions()
        for pos in head_positions:
            if pos in self.positions[3:]:
                return False
        
        # Add current position to trail
        self.trail.append(cur)
        if len(self.trail) > self.trail_length:
            self.trail.pop(0)
            
        self.positions.insert(0, new)
        if len(self.positions) > self.length:
            self.positions.pop()
        return True

    def draw(self, surface):
        # Draw trail
        for i, pos in enumerate(self.trail):
            # Calculate rainbow color based on position in trail
            hue = (i / len(self.trail)) % 1.0
            rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.8)
            color = (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
            # Make trail fade out
            alpha = int(255 * (i / len(self.trail)))
            trail_surface = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(trail_surface, (*color, alpha), 
                           (0, 0, GRID_SIZE, GRID_SIZE))
            surface.blit(trail_surface, 
                        (pos[0] * GRID_SIZE, pos[1] * GRID_SIZE))

        # Draw snake
        for i, p in enumerate(self.positions):
            if i == 0:  # Head (3x3 grid)
                # Draw 3x3 grid for head
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        # Front square (blinking mouth)
                        if dx == self.direction[0] and dy == self.direction[1]:
                            if self.mouth_timer < 5:  # Blink every 10 frames
                                continue
                        # All squares (green)
                        pygame.draw.rect(surface, GREEN, 
                                       (p[0] * GRID_SIZE + dx * GRID_SIZE,
                                        p[1] * GRID_SIZE + dy * GRID_SIZE,
                                        GRID_SIZE, GRID_SIZE))
            else:  # Body
                pygame.draw.rect(surface, GREEN, 
                               (p[0] * GRID_SIZE, p[1] * GRID_SIZE, 
                                GRID_SIZE, GRID_SIZE))

class Food:
    def __init__(self):
        self.positions = []
        self.directions = []  # Store direction for each food
        for _ in range(5):  # Create 5 food items
            self.randomize_position()
            # Add random direction for each food
            self.directions.append((random.choice([-1, 0, 1]), random.choice([-1, 0, 1])))

    def randomize_position(self):
        while True:
            new_pos = (random.randint(0, GRID_WIDTH-1), 
                      random.randint(0, GRID_HEIGHT-1))
            if new_pos not in self.positions:
                self.positions.append(new_pos)
                break

    def move_food(self):
        # Move each food item
        for i in range(len(self.positions)):
            x, y = self.positions[i]
            dx, dy = self.directions[i]
            
            # Calculate new position
            new_x = x + dx
            new_y = y + dy
            
            # Bounce off walls
            if new_x < 0 or new_x >= GRID_WIDTH:
                self.directions[i] = (-dx, dy)
                new_x = x + self.directions[i][0]
            if new_y < 0 or new_y >= GRID_HEIGHT:
                self.directions[i] = (dx, -dy)
                new_y = y + self.directions[i][1]
            
            # Update position
            self.positions[i] = (new_x, new_y)

    def draw(self, surface):
        for pos in self.positions:
            pygame.draw.rect(surface, RED,
                           (pos[0] * GRID_SIZE, 
                            pos[1] * GRID_SIZE, 
                            GRID_SIZE, GRID_SIZE))

def draw_grid():
    for x in range(0, WINDOW_WIDTH, GRID_SIZE):
        pygame.draw.line(screen, WHITE, (x, 0), (x, WINDOW_HEIGHT))
    for y in range(0, WINDOW_HEIGHT, GRID_SIZE):
        pygame.draw.line(screen, WHITE, (0, y), (WINDOW_WIDTH, y))

def show_score(snake):
    # Show score
    score_text = font.render(f'Score: {snake.score}', True, WHITE)
    screen.blit(score_text, (10, 10))
    
    # Show lives
    lives_text = font.render(f'Lives: {snake.lives}', True, WHITE)
    screen.blit(lives_text, (WINDOW_WIDTH - 100, 10))

def game_over():
    game_over_text = font.render('遊戲結束！按 SPACE 重新開始', True, WHITE)
    text_rect = game_over_text.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2))
    screen.blit(game_over_text, text_rect)
    pygame.display.flip()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    snake = Snake()
                    food = Food()
                    return

def show_title_screen():
    screen.fill(BLACK)
    
    # Draw game title
    title_text = title_font.render( 'BIG HEAD SNAKE', True, GREEN)
    title_rect = title_text.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/3))
    screen.blit(title_text, title_rect)

    # Draw game title
    title_text = title_font.render( 'by orca', True, GREEN)
    title_rect = title_text.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2))
    screen.blit(title_text, title_rect)

    # Draw start prompt
    start_text = font.render("Press SPACE to Start", True, WHITE)
    start_rect = start_text.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT*2/3))
    screen.blit(start_text, start_rect)
    
    pygame.display.update()

def main():
    clock = pygame.time.Clock()
    snake = Snake()
    food = Food()
    game_over = False
    move_counter = 0  # Counter to slow down food movement
    in_title_screen = True

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            elif event.type == pygame.KEYDOWN:
                if in_title_screen:
                    if event.key == pygame.K_SPACE:
                        in_title_screen = False
                elif game_over:
                    if event.key == pygame.K_SPACE:
                        snake = Snake()  # Reset with 3 lives
                        food = Food()
                        game_over = False
                else:
                    if event.key == pygame.K_UP and snake.direction != (0, 1):
                        snake.direction = (0, -1)
                    elif event.key == pygame.K_DOWN and snake.direction != (0, -1):
                        snake.direction = (0, 1)
                    elif event.key == pygame.K_LEFT and snake.direction != (1, 0):
                        snake.direction = (-1, 0)
                    elif event.key == pygame.K_RIGHT and snake.direction != (-1, 0):
                        snake.direction = (1, 0)

        if in_title_screen:
            show_title_screen()
            continue

        if not game_over:
            if not snake.move():
                snake.lives -= 1  # Lose a life
                if snake.lives <= 0:  # Game over when no lives left
                    game_over = True
                else:  # Reset snake position but keep score
                    snake.positions = [(GRID_WIDTH // 2, GRID_HEIGHT // 2)]
                    snake.direction = (1, 0)
                    snake.length = 1
                    snake.trail = []

            # Update mouth animation timer
            snake.mouth_timer = (snake.mouth_timer + 1) % 10

            # Move food every 5 frames to make it slower
            move_counter += 1
            if move_counter >= 5:
                food.move_food()
                move_counter = 0

            # Check for food collision with any of the food items
            head_positions = snake.get_head_positions()
            for i, food_pos in enumerate(food.positions[:]):
                if food_pos in head_positions:
                    snake.length += 1
                    snake.score += 1
                    food.positions.pop(i)  # Remove eaten food
                    food.directions.pop(i)  # Remove corresponding direction
                    food.randomize_position()  # Add new food
                    food.directions.append((random.choice([-1, 0, 1]), 
                                         random.choice([-1, 0, 1])))  # Add new direction

        screen.fill(BLACK)
        draw_grid()
        snake.draw(screen)
        food.draw(screen)

        # Draw score and lives
        show_score(snake)

        if game_over:
            game_over_text = font.render("Game Over! Press SPACE to restart", True, WHITE)
            text_rect = game_over_text.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2))
            screen.blit(game_over_text, text_rect)

        pygame.display.update()
        clock.tick(10)

if __name__ == "__main__":
    main() 