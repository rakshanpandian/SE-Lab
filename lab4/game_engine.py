import random
import pygame
from game.block import Block


class Debris:
    """Represents a sliced overhang falling off under gravity with rotation."""
    def __init__(self, x, y, width, height, color, vx=0.0):
        self.x = float(x)
        self.y = float(y)
        self.width = float(max(2.0, width))
        self.height = float(height)
        self.color = color

        self.vx = vx
        self.vy = -1.5
        self.gravity = 0.55

        self.angle = 0.0
        self.angular_vel = 4.0 if vx >= 0 else -4.0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.angle = (self.angle + self.angular_vel) % 360

    def render(self, screen):
        surf = pygame.Surface((int(self.width), int(self.height)), pygame.SRCALPHA)
        surf.fill(self.color)

        rotated_surf = pygame.transform.rotate(surf, self.angle)
        rect = rotated_surf.get_rect(center=(self.x + self.width / 2, self.y + self.height / 2))
        screen.blit(rotated_surf, rect.topleft)


class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.block_height = 28
        self.base_width = 180

        self.font_title = pygame.font.SysFont(None, 38)
        self.font_hud = pygame.font.SysFont(None, 28)
        self.font_big = pygame.font.SysFont(None, 46)
        self.font_popup = pygame.font.SysFont(None, 32, bold=True)

        # Predefined sky milestones for atmospheric altitude shift
        self.sky_stages = [
            (24, 27, 36),    # Ground / City Slate
            (20, 48, 88),    # Twilight Blue (~Tier 7)
            (65, 30, 85),    # Dusk Purple   (~Tier 15)
            (16, 20, 52),    # Deep Cosmic   (~Tier 25)
            (8, 8, 14),      # Stratosphere Void (~Tier 35+)
        ]

        self.reset()

    def get_color(self, index):
        palette = [
            (230, 75, 75),   # Crimson
            (240, 140, 45),  # Orange
            (245, 210, 50),  # Gold
            (60, 195, 110),  # Green
            (50, 150, 240),  # Blue
            (165, 80, 225),  # Purple
        ]
        return palette[index % len(palette)]

    def get_sky_color(self):
        """Computes a smooth interpolated RGB background color based on stack height."""
        # Advance through a new sky tier every 7-8 placed blocks
        tier_span = 7.5
        t = (len(self.stack) - 1) / tier_span
        max_idx = len(self.sky_stages) - 1

        idx = int(t)
        if idx >= max_idx:
            return self.sky_stages[-1]

        frac = t - idx
        c1 = self.sky_stages[idx]
        c2 = self.sky_stages[idx + 1]

        # Smooth linear blend across R, G, B channels
        r = int(c1[0] + (c2[0] - c1[0]) * frac)
        g = int(c1[1] + (c2[1] - c1[1]) * frac)
        b = int(c1[2] + (c2[2] - c1[2]) * frac)
        return (r, g, b)

    def reset(self):
        self.score = 0
        self.game_over = False

        self.perfect_streak = 0
        self.popup_timer = 0
        self.popup_pos = (0, 0)
        self.debris_list = []

        # Ambient background stars that slowly reveal and drift
        self.stars = [
            [random.randint(0, self.width), random.randint(0, self.height), random.uniform(0.3, 1.0)]
            for _ in range(45)
        ]

        base_x = (self.width - self.base_width) // 2
        base_y = self.height - 60
        base_block = Block(base_x, base_y, self.base_width, self.block_height, self.get_color(0), speed=0)
        self.stack = [base_block]

        self.spawn_active_block()

    def spawn_active_block(self):
        top_block = self.stack[-1]
        next_y = top_block.y - self.block_height - 4
        speed = min(10.0, 4.5 + (len(self.stack) * 0.35))
        color = self.get_color(len(self.stack))

        start_x = 25 if random.choice([True, False]) else self.width - 25 - top_block.width
        self.active_block = Block(start_x, next_y, top_block.width, self.block_height, color, speed=speed)

    def spawn_debris_slice(self, x, y, width, height, color, vx):
        if width > 0:
            self.debris_list.append(Debris(x, y, width, height, color, vx=vx))

    def drop_block(self):
        if self.game_over:
            return

        top_block = self.stack[-1]
        act = self.active_block

        alignment_error = abs(act.x - top_block.x)
        is_perfect = alignment_error <= 3

        left = max(act.x, top_block.x)
        right = min(act.x + act.width, top_block.x + top_block.width)
        overlap = right - left

        is_successful_drop = overlap > 0

        if is_successful_drop:
            if is_perfect:
                left = top_block.x
                trimmed_width = top_block.width
                self.perfect_streak += 1
                self.score += 2

                if self.perfect_streak >= 3:
                    expansion = 10.0
                    new_width = min(float(self.base_width), trimmed_width + expansion)
                    left -= (new_width - trimmed_width) / 2
                    trimmed_width = new_width

                self.popup_timer = 45
                self.popup_pos = (left + trimmed_width / 2, act.y - 18)
            else:
                self.perfect_streak = 0
                trimmed_width = max(10.0, overlap)
                self.score += 1

                # Left overhang slice
                if act.x < top_block.x:
                    cut_width = top_block.x - act.x
                    self.spawn_debris_slice(act.x, act.y, cut_width, self.block_height, act.color, vx=-2.2)

                # Right overhang slice
                act_right = act.x + act.width
                top_right = top_block.x + top_block.width
                if act_right > top_right:
                    cut_width = act_right - top_right
                    cut_x = top_right
                    self.spawn_debris_slice(cut_x, act.y, cut_width, self.block_height, act.color, vx=2.2)

            new_block = Block(left, act.y, trimmed_width, self.block_height, act.color, speed=0)
            self.stack.append(new_block)

            # Camera downward scroll
            if new_block.y < 180:
                shift_amount = self.block_height + 4
                for b in self.stack:
                    b.y += shift_amount
                for d in self.debris_list:
                    d.y += shift_amount
                for star in self.stars:
                    star[1] = (star[1] + shift_amount * 0.4) % self.height
                if self.popup_timer > 0:
                    self.popup_pos = (self.popup_pos[0], self.popup_pos[1] + shift_amount)

            self.spawn_active_block()
        else:
            fall_dir = 3.0 if act.x > top_block.x else -3.0
            self.spawn_debris_slice(act.x, act.y, act.width, self.block_height, act.color, vx=fall_dir)
            self.game_over = True

    def handle_event(self, event):
        if self.game_over:
            if (event.type == pygame.KEYDOWN and (event.key == pygame.K_r or event.key == pygame.K_SPACE)) or \
               (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                self.reset()
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.drop_block()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.drop_block()

    def update(self):
        if not self.game_over:
            self.active_block.update(self.width)

        if self.popup_timer > 0:
            self.popup_timer -= 1

        for d in self.debris_list:
            d.update()
        self.debris_list = [d for d in self.debris_list if d.y < self.height + 60]

    def render(self, screen):
        # Task 4: Dynamic background color based on altitude
        sky_color = self.get_sky_color()
        screen.fill(sky_color)

        # Soft atmospheric star twinkle (more visible as the player reaches higher altitudes)
        if len(self.stack) > 8:
            star_alpha = min(220, (len(self.stack) - 8) * 12)
            for sx, sy, brightness in self.stars:
                color = (int(star_alpha * brightness), int(star_alpha * brightness), int(star_alpha * brightness))
                screen.set_at((int(sx), int(sy)), color)

        title_surf = self.font_title.render("Skyscraper Stack", True, (245, 245, 245))
        screen.blit(title_surf, (self.width // 2 - title_surf.get_width() // 2, 16))

        score_surf = self.font_hud.render(f"Height: {self.score}", True, (255, 220, 80))
        screen.blit(score_surf, (self.width // 2 - score_surf.get_width() // 2, 54))

        # Render debris behind active blocks
        for d in self.debris_list:
            d.render(screen)

        for b in self.stack:
            b.render(screen)

        if not self.game_over:
            self.active_block.render(screen)

        # "PERFECT!" popup
        if self.popup_timer > 0:
            popup_surf = self.font_popup.render("PERFECT!", True, (255, 215, 0))
            px = int(self.popup_pos[0] - popup_surf.get_width() // 2)
            py = int(self.popup_pos[1] - popup_surf.get_height() // 2)
            screen.blit(popup_surf, (px, py))

        # Collapse overlay
        if self.game_over:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 195))
            screen.blit(overlay, (0, 0))

            over_surf = self.font_big.render("TOWER COLLAPSED!", True, (240, 75, 75))
            screen.blit(over_surf, (self.width // 2 - over_surf.get_width() // 2, self.height // 2 - 40))

            final_surf = self.font_hud.render(f"Final Height: {self.score}", True, (255, 255, 255))
            screen.blit(final_surf, (self.width // 2 - final_surf.get_width() // 2, self.height // 2 + 10))

            restart_surf = self.font_hud.render("Press [Space] or [R] to Play Again", True, (200, 200, 200))
            screen.blit(restart_surf, (self.width // 2 - restart_surf.get_width() // 2, self.height // 2 + 50))