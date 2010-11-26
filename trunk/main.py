#!/usr/bin/env python
import sys
import math
import time
import random
random.seed(time.time())

import optparse

#from OpenGL.GL import *
#from OpenGL.GLU import *

import pygame
from pygame.locals import *



class Stats(object):
  stats_object = None
  @staticmethod
  def get_stats(screen = None, size = None):
    if Stats.stats_object is None:
      Stats.stats_object = Stats(screen, size)
    return Stats.stats_object

  MARGIN = 20

  def __init__(self, screen, size):
    self.screen = screen
    self.size = self.width,self.height = size
    self.font = pygame.font.SysFont("courier", 10)
    self.counts = {}

  def reset(self, varname = None):
    if varname is None:
      self.counts = {}
    else:
      self.counts[varname] = 0

  def inc(self, varname):
    if self.counts.has_key(varname):
      self.counts[varname] += 1
    else:
      self.counts[varname] = 1

  def draw(self):
    x = self.width - self.MARGIN
    y = self.MARGIN
    for key in self.counts:
      string = "%s: % 8d" % (key, self.counts[key])
      w,h = self.font.size(string)
      self.screen.blit(self.font.render(string, False,
              (255,255,255)), (x-w, y))
      y += h


class Ship(object):
  '''This class is used for drawing, mainly.  Just pass it some points
  and things, and it'll handle the rest!'''
  def __init__(self, screen, color, points, pos=(0,0), traj=0, size=10):
    '''Create this!
    screen: The screen to draw on
    color: The color to draw
    points: Points consisting of the line-art
    pos: Initial position of the ship
    traj: Initial trajectory (0 radians is to the left, .5pi is down)
    size: Size of the ship.
    
    Something perhaps non-trivial, is that the size parameter is in pixels,
    but so are the points.  So if the size is 5 but there's a point in the
    points list that's something like "(40,80)", then the effect will be that
    the effectual size of the ship will be sqrt(40**2+80**2) * 5 = 447.2, so
    beware.  It is recommended that you try to keep the values in the points
    argument to <= 1.'''

    self.screen = screen
    self.color = color
    self.ps = points
    self.pos = list(pos)
    self.traj = traj
    self.size = size

    # rect ensures the bbox for this is calculated at most once per tick
    self.rect = None   # i.e., not up-to-date

  def move(self, dx, dy):
    self.rect = None
    self.pos[0] += dx
    self.pos[1] += dy

  def move_forward(self, speed):
    self.rect = None
    self.pos[0] += math.cos(self.traj) * speed
    self.pos[1] += math.sin(self.traj) * speed

  def rotate(self, dt):
    self.rect = None
    self.traj += dt
    while self.traj > 2 * math.pi:
      self.traj -= 2 * math.pi
    while self.traj < 0:
      self.traj += 2 * math.pi

  def _calc_global_ps(self):
    st = math.sin(self.traj) * self.size
    ct = math.cos(self.traj) * self.size
    return map(lambda p: [self.pos[0] + p[0] * ct - p[1] * st,
                          self.pos[1] + p[1] * ct + p[0] * st],
               self.ps)

  def _build_rect(self):
    if self.rect is None:
      ps = self._calc_global_ps()
      self.rect = pygame.Rect(ps[0],(0,0))
      for i in xrange(1,len(ps)):
        self.rect.union_ip(pygame.Rect(ps[i], (0,0)))
    return self.rect

  def center(self):
    return self._build_rect().center

  def draw(self):
    pygame.draw.lines(self.screen, self.color, True, self._calc_global_ps())

  def collides(self, that):
    if isinstance(that, Ship):
      return self._build_rect().colliderect(that._build_rect())
    elif isinstance(that, Bullet):
      # Bullets vary greatly in how their collision detection
      # is meant to work.
      return that.collides(self)
    else:
      print 'Warning! Ship-%d collision detection??' % type(that)
      return False



class Player(Ship):
  '''This should be unique in that it's the only ship that can also fire guns
  and stuff.'''
  def __init__(self, screen):
    Ship.__init__(self, screen, (200, 200, 255),
                  [ [ 0, -1], [ 2, -1], [ 0, -2], [-2, -1],
                    [ 0, -1], [ 0,  1], [ 2,  1], [ 0,  2],
                    [-2,  1], [ 0,  1], [-2, -1], [-2,  1] ],
                  size = 5)
    self.last_fire_time = 0
    self.fire_delay = 100 # ms
    self.exploding = False
    self.expl_prog = 0
    self.gun = Gun(screen, 0)

  def okay_to_fire(self):
    ticks = pygame.time.get_ticks()
    if self.last_fire_time + self.fire_delay <= ticks:
      self.last_fire_time = ticks
      return True
    return False

  def draw(self):
    if self.exploding:
      self.expl_prog += .5
      pygame.draw.circle(self.screen, (255,0,0), 
          (int(self.pos[0]),int(self.pos[1])), int(self.expl_prog))
    else:
      Ship.draw(self)

  def fire(self, traj):
    return self.okay_to_fire() and self.gun.fire(self.pos, traj) or ()

  def explode(self):
    self.exploding = True

  @staticmethod
  def spawn_at(screen, x, y):
    ship = Player(screen)
    ship.pos = [x,y]
    return ship



##########################################################################
#                               Bullets                                  #
##########################################################################

class Bullet(object):
  def __init__(self, screen, pos, traj):
    self.screen = screen
    self.pos = list(pos)
    self.traj = traj
    self.speed = 4.
    self.length = 10
    self.color = 255,0,0

  def collides(self, that):
    if not isinstance(that, Ship):
      print 'Warning!  Bullet-non-Ship collision check???'
      return False
    return that._build_rect().collidepoint(self.pos)

  def _calc_shift(self):
    return [ self.speed * math.cos(self.traj),
             self.speed * math.sin(self.traj) ]

  def _calc_tail_pos(self):
    return [ self.pos[0] - self.length * math.cos(self.traj),
             self.pos[1] - self.length * math.sin(self.traj) ]

  def draw(self):
    pygame.draw.line(self.screen, self.color,
                     self.pos, self._calc_tail_pos(), 2)

  def tick(self):
    self.move_forward()

  def move_forward(self):
    shift = self._calc_shift()
    self.pos[0] += shift[0]
    self.pos[1] += shift[1]

class Gun(object):
  def __init__(self, screen, num_bullets = 1):
    self.screen = screen
    self.power = num_bullets

  def fire(self, pos, traj):
    bullets = []
    for i in xrange(-self.power, self.power + 1, 2):
      bullets.append(Bullet(self.screen, pos, traj + i / 100.))
    return bullets



##########################################################################
#                               Baddies                                  #
##########################################################################

class Baddie(Ship):
  def __init__(self, screen, color, pos, traj, size, geom):
    Ship.__init__(self, screen, color, geom, size = size)
    self.pos = list(pos)
    self.traj = traj
    self.speed = .5

  def tick(self):
    '''Perform one frame of action.'''
    print 'Warning: Baddie.tick() called'

class Wiggler(Baddie):
  def __init__(self, screen, pos, traj):
    Baddie.__init__(self, screen, (0,255,0), pos, traj, 5,
            ((1,1), (1,-1), (-1,-1), (-1, 1)))

  def tick(self):
    '''Perform one frame of action.'''
    self.traj += random.randrange(-100,100,1) / 1000.
    while self.traj > 2 * math.pi: self.traj -= 2 * math.pi
    while self.traj < 0: self.traj += 2 * math.pi
    self.move_forward(self.speed)

class Homer(Baddie):
  def __init__(self, screen, pos, traj):
    Baddie.__init__(self, screen, (255,0,255), pos, traj, 5,
            ((2,0), (0,-1), (-2,0), (0,1)))
    self.speed = .4
    self.dt = .01  # max change in traj

  def tick(self):
    '''Perform one frame of action.'''
    dx = Main.get_main().player.pos[0] - self.pos[0]
    dy = Main.get_main().player.pos[1] - self.pos[1]
    self.traj = math.atan2(dy, dx)
    self.move_forward(self.speed)



class SpawnPoint(object):
  def __init__(self, screen, size, x, y, baddies_array):
    self.screen = screen
    self.pos = [x,y]
    self.baddies = baddies_array
    self.traj = math.atan2(size[0] / 2 - y, size[1] / 2 - x)
    self.queue = []
    self.paused = False

  def pause(self):
    self.paused = True

  def resume(self):
    self.paused = False

  def spawn(self, baddie_type = Wiggler):
    self.baddies.append(baddie_type(self.screen, self.pos, self.traj))

  def queue_spawn(self, baddie_type):
    self.queue.append(baddie_type)

  def tick(self):
    if self.paused: return
    if len(self.queue) > 0 and random.randrange(100) < 20:
      self.spawn(self.queue[0])
      del self.queue[0]

  def draw(self):
    pass

  def clear(self):
    self.queue = []



class Level(object):
  def __init__(self, screen, size, spawn_point_array, greeting, progression):
    '''Creates a level.
    screen: SDL surface to draw to
    spawn_point_array: the spawn points
    greeting: the string to display when the level starts
    progression: The progression of the level.  Expected is a list of
                 4-tuples, where each tuple is:
                   1: pause time before wave start
                   2: index of spawn point to spawn at.
                   3: type of baddie to spawn
                   4: number of baddies to spawn'''
    self.screen = screen
    self.spawns = spawn_point_array

    self.font = pygame.font.SysFont("courier", 30, bold = True)
    self.greeting = greeting
    w,h = self.font.size(self.greeting)
    self.greeting_pos = (size[0] - w) / 2, (size[1] - h) / 2

    self.progression = progression
    self.prog_i = -1
    self.paused = False

  def started(self):
    return self.prog_i >= 0

  def pause(self):
    self.paused = pygame.time.get_ticks()
    for sp in self.spawns: sp.pause()
    
  def resume(self):
    for sp in self.spawns: sp.resume()
    self.start_time += pygame.time.get_ticks() - self.paused
    self.paused = False

  def start(self):
    self.paused = False
    self.prog_i = 0
    self.start_time = pygame.time.get_ticks()

  def _p(self):
    if self.prog_i < len(self.progression):
      return self.progression[self.prog_i]
    else:
      return (9e9999,-1,None,0)

  def tick(self):
    if self.paused: return

    # Check/spawn queue
    if self.prog_i < len(self.progression):
      while self._p()[0] <= pygame.time.get_ticks() - self.start_time:
        for i in xrange(self._p()[3]):
          self.spawns[self._p()[1]].queue_spawn(self._p()[2])
        self.prog_i += 1

  def jump_to_next_wave(self):
    if self.prog_i != 0 and self.prog_i < len(self.progression):
      self.start_time = pygame.time.get_ticks() - self._p()[0]
    self.tick()

  def draw(self):
    if self.prog_i == 0:
      self.screen.blit(self.font.render(self.greeting, False,
              (255,255,255)), self.greeting_pos)

  def done(self):
    return self.prog_i >= len(self.progression)


class Input(object):
  def __init__(self):
    if pygame.joystick.get_count() > 0:
      self.js = pygame.joystick.Joystick(0)
      self.js.init()
      if self.js.get_numaxes() < 4:
        self.js.quit()
        self.js = None
        return
      print 'using %d axes' % self.js.get_numaxes()
    else:
      self.js = None

  def get_mx(self):
    '''Gets movement in the X direction (in [-1,1] for [left,right]).'''
    if self.js is None:
      keys = pygame.key.get_pressed()
      if keys[pygame.K_f]:
        return 1.
      elif keys[pygame.K_s]:
        return -1.
      else:
        return .0
    else:
      return self.js.get_axis(0)

  def get_my(self):
    '''Gets movement in the Y direction (in [-1,1] for [top,bottom]).'''
    if self.js is None:
      keys = pygame.key.get_pressed()
      if keys[pygame.K_d]:
        return 1.
      elif keys[pygame.K_e]:
        return -1.
      else:
        return .0
    else:
      return self.js.get_axis(1)

  def get_fx(self):
    '''Gets fire direction in X (in [-1,1] for [left,right]).'''
    if self.js is None:
      keys = pygame.key.get_pressed()
      if keys[pygame.K_l]:
        return 1.
      elif keys[pygame.K_j]:
        return -1.
      else:
        return .0
    else:
      return self.js.get_axis(2)

  def get_fy(self):
    '''Gets fire direction in Y (in [-1,1] for [top,bottom]).'''
    if self.js is None:
      keys = pygame.key.get_pressed()
      if keys[pygame.K_k]:
        return 1.
      elif keys[pygame.K_i]:
        return -1.
      else:
        return .0
    else:
      return self.js.get_axis(3)



class CollisionSpace(object):
  BINSIZE = 50
  BUFSIZE = .2

  def __init__(self, size, player):
    self.size = self.width,self.height = size
    self.player = player
    self.cols = size[0] / self.BINSIZE
    self.rows = size[1] / self.BINSIZE
    self.baddies = []
    self.bullets = []

  def empty(self):
    self.baddies = []
    self.bullets = []

  def _tick_baddie(self, baddie):
    baddie.tick()
    rect = baddie._build_rect()
    if rect.left <= 0 or rect.right >= self.width:
      baddie.traj = math.pi - baddie.traj
      while baddie._build_rect().left <= 0:
        baddie.move(1,0)
      while baddie._build_rect().right >= self.width:
        baddie.move(-1,0)

    if rect.top <= 0 or rect.bottom >= self.height:
      baddie.traj = -baddie.traj
      while baddie._build_rect().top <= 0:
        baddie.move(0,1)
      while baddie._build_rect().bottom >= self.height:
        baddie.move(0,-1)
    self._insert_baddie(baddie)

  def tick(self):
    self.bins = []
    for i in xrange(self.cols):
      self.bins.append([])
      for j in xrange(self.rows):
        self.bins[i].append([])

    Stats.get_stats().counts['num_bins'] = self.rows * self.cols
    Stats.get_stats().counts['baddies'] = len(self.baddies)
    Stats.get_stats().counts['bullets'] = len(self.bullets)

    # update baddies and put them in their bins
    for b in self.baddies:
      self._tick_baddie(b)

    # update ship, bound in the square, and check collisions
    for i,j in self._get_bins_idxs(self.player):
      for b in self.bins[i][j]:
        if b.collides(self.player):
          self.player.explode()
          break
      if self.player.exploding: break

    # update bullets and delete when O.O.B.
    for b1 in xrange(len(self.bullets)-1,-1,-1):
      self.bullets[b1].tick()
      pos = self.bullets[b1].pos
      w,h = self.size
      if pos[0] < 0 or pos[1] < 0 or pos[0] > w or pos[1] > h:
        del self.bullets[b1]
      else:
        removed = False
        for i,j in self._get_bins_idxs(self.bullets[b1]):
          for b2 in xrange(len(self.bins[i][j])-1,-1,-1):
            Stats.get_stats().inc("comparisons")
            if self.bins[i][j][b2].collides(self.bullets[b1]):
              self._remove_bullet(self.bullets[b1])
              self._remove_baddie(self.bins[i][j][b2])
              removed = True
              break
          if removed: break

  def _get_simple_bins_idxs(self, obj):
    Stats.get_stats().inc("_get_simple_bins_idxs")
    pos = ( float(obj.pos[0]) / self.size[0] * self.cols,
            float(obj.pos[1]) / self.size[1] * self.rows )
    bin_i = int(pos[0])
    bin_j = int(pos[1])
    i_pos = pos[0] - bin_i
    j_pos = pos[1] - bin_j

    if bin_i < 0:
      bin_i = 0
    elif bin_i >= self.cols:
      bin_i = self.cols - 1
    if bin_j < 0:
      bin_j = 0
    elif bin_j >= self.rows:
      bin_j = self.rows - 1

    return bin_i,bin_j

  def _get_bins_idxs(self, obj):
    Stats.get_stats().inc("_get_bins_idxs")
    pos = ( float(obj.pos[0]) / self.size[0] * self.cols,
            float(obj.pos[1]) / self.size[1] * self.rows )
    bin_i = int(pos[0])
    bin_j = int(pos[1])
    i_pos = pos[0] - bin_i
    j_pos = pos[1] - bin_j

    skip_col_ovrlp = skip_row_ovrlp = False
    if bin_i < 0:
      bin_i = 0
      skip_col_ovrlp = True
    elif bin_i >= self.cols:
      bin_i = self.cols - 1
      skip_col_ovrlp = True
    if bin_j < 0:
      bin_j = 0
      skip_row_ovrlp = True
    elif bin_j >= self.rows:
      bin_j = self.rows - 1
      skip_row_ovrlp = True

    l_bin = r_bin = False
    bins = [(bin_i, bin_j)]
    if not skip_col_ovrlp:
      if i_pos < self.BUFSIZE:
        if bin_i > 0:
          l_bin = True
          bins.append((bin_i-1, bin_j))
      elif i_pos > 1 - self.BUFSIZE:
        if bin_i < self.cols - 1:
          r_bin = True
          bins.append((bin_i+1, bin_j))

    if not skip_row_ovrlp:
      if j_pos < self.BUFSIZE:
        if bin_j > 0:
          bins.append((bin_i, bin_j-1))
          if l_bin:
            bins.append((bin_i-1, bin_j-1))
          elif r_bin:
            bins.append((bin_i+1, bin_j-1))
      elif j_pos > 1 - self.BUFSIZE:
        if bin_j < self.rows - 1:
          bins.append((bin_i, bin_j))
          if l_bin:
            bins.append((bin_i-1, bin_j+1))
          elif r_bin:
            bins.append((bin_i+1, bin_j+1))

    #if self.player == obj:
    #  print '           num bins:', len(bins)
    #  sys.stdout.flush()
    return bins
    
  def _insert_baddie(self, b):
    i,j = self._get_simple_bins_idxs(b)
    self.bins[i][j].append(b)

  def _remove_bullet(self, b):
    self.bullets.remove(b)

  def _remove_baddie(self, b, idxs = None):
    if idxs is None:
      idxs = self._get_simple_bins_idxs(b)
    self.bins[idxs[0]][idxs[1]].remove(b)
    self.baddies.remove(b)

  def add(self, obj):
    if isinstance(obj, Bullet):
      self.bullets.append(obj)
    elif isinstance(obj, Baddie):
      self.baddies.append(obj)
    else:
      print 'Unrecognized type in CollisionSpace.add():', type(obj)

  def draw(self):
    #for x in xrange(self.BINSIZE, self.size[0], self.BINSIZE):
    #  pygame.draw.line(Main.get_main().screen, (0,0,255), (x,0), (x,self.size[1]), 1)
    #for y in xrange(self.BINSIZE, self.size[1], self.BINSIZE):
    #  pygame.draw.line(Main.get_main().screen, (0,0,255), (0,y), (self.size[0],y), 1)
    for b in self.baddies: b.draw()
    for b in self.bullets: b.draw()



class Main(object):
  def __init__(self, options):
    assert self.MAIN_OBJECT is None, "Another Main object is being created!"

    pygame.init()
    self.size = self.width, self.height = options.size
    self.screen = pygame.display.set_mode(self.size, HWSURFACE | DOUBLEBUF)
    self.stats = Stats.get_stats(self.screen, self.size)

    self.player = Player.spawn_at(self.screen, self.width/2, self.height/2)
    self.speed = 2
    self.black = (0,0,0)

    self.fps_timer = pygame.time.Clock()
    self.fps = 30

    # fonts
    self.score_font = pygame.font.SysFont('courier', 25, bold = True)
    self.debug_font = pygame.font.SysFont('arial', 8)
    self.gameover_font = pygame.font.SysFont('arial', 18, bold = True)
    self.gameover_pos = self.gameover_font.size('GAME OVER')
    self.gameover_pos = (self.width - self.gameover_pos[0]) / 2, \
                        (self.height - self.gameover_pos[1]) / 2
    self.winner_font = pygame.font.SysFont('arial', 18, bold = True)
    self.winner_pos = self.winner_font.size('WINNER')
    self.winner_pos = (self.width - self.winner_pos[0]) / 2, \
                      (self.height - self.winner_pos[1]) / 2

    self.user_input = Input()
    self.space = CollisionSpace(self.size, self.player)
    dw, dh = .1 * self.width, .1 * self.height
    self.spawn_points = [
        SpawnPoint(self.screen, self.size,
                             dw,               dh, self.space.baddies),
        SpawnPoint(self.screen, self.size,
                             dw, self.height - dh, self.space.baddies),
        SpawnPoint(self.screen, self.size,
                self.width - dw,               dh, self.space.baddies),
        SpawnPoint(self.screen, self.size,
                self.width - dw, self.height - dh, self.space.baddies) ]
    self.score = 0
    self.winner = False

    self.lev_i = 2
    self.levels = [ Level(self.screen, self.size, self.spawn_points,
                          "Level 1", [ (2e3, 0, Wiggler, 20),
                                       (2e3, 1, Wiggler, 20),
                                       (2e3, 2, Homer,   20),
                                       (2e3, 3, Wiggler, 20) ]),
                    Level(self.screen, self.size, self.spawn_points,
                          "Level 2", [ (2e3, 0, Wiggler, 20),
                                       (2e3, 1, Homer,   20),
                                       (2e3, 2, Wiggler, 20),
                                       (2e3, 3, Homer,   20),
                                       (1e4, 1, Homer,   20),
                                       (1e4, 2, Wiggler, 20),
                                       (1e4, 1, Homer,   20),
                                       (1e4, 2, Wiggler, 20) ]),
                    Level(self.screen, self.size, self.spawn_points,
                          "Level 3", [ (2e3, 0, Wiggler, 2000),
                                       (2e3, 1, Wiggler, 2000),
                                       (2e3, 2, Wiggler, 2000),
                                       (2e3, 3, Wiggler, 2000),
                                       (1e4, 3, Homer,   2000) ]) ]


  def run(self):

    ######################################################################
    #                              Main Loop                             #
    ######################################################################

    self.levels[self.lev_i].start()

    while True:
      self.fps_timer.tick(self.fps)
      if self.levels[self.lev_i].paused:
        if self.fps_timer.get_fps() >= self.fps:
          self.levels[self.lev_i].resume()
      else:
        if self.fps_timer.get_fps() < self.fps:
          self.levels[self.lev_i].pause()



      ####################################################################
      #                            User Input                            #
      ####################################################################

      # Quitting and special keys.
      for event in pygame.event.get([pygame.QUIT, pygame.KEYUP]):
        if event.type == pygame.QUIT:
          sys.exit()
        if event.type == pygame.KEYUP:
          if (event.key == pygame.K_q or event.key == pygame.K_w) and \
             (event.mod == pygame.K_RCTRL or event.mod == pygame.K_LCTRL):
            sys.exit()
          elif event.key == pygame.K_F7:
            self.spawn_points[random.randrange(len(self.spawn_points))].spawn()
          elif event.key == pygame.K_RIGHTBRACKET:
            self.player.gun.power += 1
          elif event.key == pygame.K_LEFTBRACKET:
            if self.player.gun.power > 0:
              self.player.gun.power -= 1
          elif event.key == pygame.K_F6:
            print 'stats:'
            print '  Num Baddies:', len(self.space.baddies)
            print '  Num Bullets:', len(self.space.bullets)
      pygame.event.clear()

      # Movement
      if self.player.exploding:
        # explode and restart
        if self.player.expl_prog >= 30:
          for s in self.spawn_points: s.clear()
          del self.player
          self.player = Player.spawn_at(self.screen, self.width / 2, self.height / 2)
          self.space.empty()
          self.score = 0
          self.levels[self.lev_i].start()
      else:
        js_dx = self.user_input.get_mx()
        js_dy = self.user_input.get_my()
        self.player.traj = math.atan2(js_dy, js_dx)
        if abs(js_dx) > .1 or abs(js_dy) > .1:
          amt = math.sqrt(js_dx * js_dx + js_dy * js_dy)
          if amt > 1:
            amt = 1.
          elif amt < -1:
            amt = -1.
          self.player.move_forward(self.speed * amt)

        # Fire
        js_fx = self.user_input.get_fx()
        js_fy = self.user_input.get_fy()
        if abs(js_fx) > .1 or abs(js_fy) > .1:
          for b in self.player.fire(math.atan2(js_fy, js_fx)):
            self.space.add(b)


        ##################################################################
        #                      Collision Detection                       #
        ##################################################################

        while self.player._build_rect().left <= 0:
          self.player.move(1,0)
        while self.player._build_rect().right >= self.width:
          self.player.move(-1,0)
        while self.player._build_rect().top <= 0:
          self.player.move(0,1)
        while self.player._build_rect().bottom >= self.height:
          self.player.move(0,-1)


      ####################################################################
      #                        Level Progression                         #
      ####################################################################

      if self.lev_i < len(self.levels) and self.no_more_baddies():
        if self.levels[self.lev_i].done():
          self.lev_i += 1
          if self.lev_i < len(self.levels):
            self.levels[self.lev_i].start()
          else:
            self.winner = True
        else:
          self.levels[self.lev_i].jump_to_next_wave()
      elif not self.winner:
        self.levels[self.lev_i].tick()

      self.space.tick()
      #for b in self.baddies: b.tick()
      #for b in self.bullets: b.tick()
      for s in self.spawn_points: s.tick()
      


      ####################################################################
      #                         Drawing Process                          #
      ####################################################################

      self.screen.fill(self.black)

      for s in self.spawn_points: s.draw()

      self.space.draw()

      if self.lev_i < len(self.levels):
        self.levels[self.lev_i].draw()
      
      if self.winner:
        self.screen.blit(self.winner_font.render("WINNER", False,
            (255,255,255)), self.winner_pos)
      if self.player.exploding:
        self.screen.blit(self.gameover_font.render("GAME OVER", False,
            (255,255,255)), self.gameover_pos)
      self.screen.blit(self.score_font.render('%d' % self.score,
          False, (255,255,255)), (10,10))
      #self.screen.blit(self.score_font.render('{:,}'.format(self.score),
      #    False, (255,255,255)), (10,10))

      self.player.draw()
      self.stats.counts['FPS'] = self.fps_timer.get_fps()
      self.stats.draw()
      self.stats.reset()
      pygame.display.flip()

  def spawn_points_empty(self):
    for sp in self.spawn_points:
      if len(sp.queue) != 0:
        return False
    return True

  def no_more_baddies(self):
    return self.spawn_points_empty() and len(self.space.baddies) <= 0

  # singleton enforcement ... and acts as a global variable
  MAIN_OBJECT = None
  @staticmethod
  def get_main(options=None):
    if Main.MAIN_OBJECT is None:
      Main.MAIN_OBJECT = Main(options)
    elif options is not None:
      assert len(args) > 0, "Main object already created and arguments passed!"
    return Main.MAIN_OBJECT


def parse_args():
  '''Parses the command line arguments and returns an option object.'''
  op = optparse.OptionParser()
  op.set_defaults(config = '~/.linebattlesrc',
                  input_type = 'none')
  op.add_option('-C', '--config', help="Use a different config file.")
  op.add_option('-j', '--input', dest='input_type',
                type='choice', choices=('none','keyboard','joystick'),
                help="Force use of the joystick.")
  op.add_option('-s', '--size', default='800x600',
                action='store', type='string',
                help="Set the window resolution.")
  (options, args) = op.parse_args()

  try:
    options.size = map(lambda x: int(x), options.size.split('x'))
  except ValueError:
    op.error('Invalid size parameter: "%s"' % options.size)
  finally:
    if len(options.size) != 2:
      op.error('Invalid size parameter: "%s"' %
          reduce(lambda a,b: '%sx%s' % (a,b), options.size))

  if len(args) > 0:
    print 'Unrecognized option:', args[0]
    sys.exit()

  return options


if __name__ == '__main__':
  Main.get_main(parse_args()).run()
