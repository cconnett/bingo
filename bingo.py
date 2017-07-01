from queue import PriorityQueue, Empty
import itertools
import json
import random
import threading
import time

import requests

inq = PriorityQueue()
outq = PriorityQueue()

# lock = threading.RLock()
hi_seed = 1000001

FULL_ITEM_LIST = [
    "Kokiri Sword", "Razor Sword", "Gilded Sword", "Adult Wallet",
    "Giant's Wallet", "Big Bomb Bag", "Biggest Bomb Bag", "Large Quiver",
    "Largest Quiver", "Hero's Shield", "Bomber's Notebook", "Moon's Tear",
    "Land Title Deed", "Swamp Title Deed", "Ocean Title Deed",
    "Mountain Title Deed", "Room Key", "Pendant of Memories",
    "Express Mail to Mama", "Letter to Kafei", "Hero's Bow", "Fire Arrows",
    "Ice Arrows", "Light Arrows", "Deku Stick", "Deku Nut (1)",
    "Deku Nuts (10)", "Magic Bean", "Pictograph Box", "Powder Keg", "Hookshot",
    "Great Fairy's Sword", "Postman's Hat", "All-Night Mask", "Blast Mask",
    "Stone Mask", "Great Fairy Mask", "Keaton Mask", "Bremen Mask",
    "Bunny Hood", "Don Gero's Mask", "Mask of Scents", "Romani's Mask",
    "Circus Leader's Mask", "Kafei's Mask", "Couple's Mask", "Mask of Truth",
    "Kamaro's Mask", "Gibdo Mask", "Garo's Mask", "Captain's Hat",
    "Giant's Mask", "Fierce Deity's Mask", "Transformation Mask"
]

horizontal_bingos = [
    [0, 1, 2, 3, 4],
    [5, 6, 7, 8, 9],
    [10, 11, 12, 13, 14],
    [15, 16, 17, 18, 19],
    [20, 21, 22, 23, 24],
]
vertical_bingos = [
    [0, 5, 10, 15, 20],
    [1, 6, 11, 16, 21],
    [2, 7, 12, 17, 22],
    [3, 8, 13, 18, 23],
    [4, 9, 14, 19, 24],
]
diagonal_bingos = [
    [0, 6, 12, 18, 24],
    [4, 8, 12, 16, 20],
]

bingos = horizontal_bingos + vertical_bingos + diagonal_bingos

itemList = set()
hi_score = (0, 0)


def add(item):
  if item in itemList:
    return
  itemList.add(item)
  global inq, outq, old_inq
  old_inq = inq
  inq = outq
  outq = PriorityQueue()
  try:
    while True:
      inq.put(old_inq.get(block=False))
  except Empty:
    pass


def genCardArray(key):
  rng = PRNG(mixkey(key))
  source = FULL_ITEM_LIST[:]
  for i in range(25):
    index = int(rng.double() * len(source))
    item = source[index]
    source[index:index + 1] = []
    if item == "Transformation Mask":
      item = ["Deku Mask", "Goron Mask", "Zora Mask"][int(rng.double() * 3)]
    yield item


def mixkey(seed):
  # smear = 0
  j = 0
  key = [0] * len(seed)
  for j in range(len(seed)):
    #smear ^= key[j % WIDTH] * 19
    key[j] = ord(seed[j]) % WIDTH
  return key


class Worker(threading.Thread):
  def run(self):
    while True:
      global hi_score, inq, outq
      try:
        _, _, _, seed, board = inq.get(block=False)
      except Empty:
        if hi_seed < 5000000:
          _, _, _, seed, board = self.NewCard()
        else:
          time.sleep(1.1)

      # Check seed
      hits = len(itemList & set(board))
      if hits == 24: print(set(board) - itemList)
      num_bingos = sum(
          all(board[i] in itemList for i in bingo) for bingo in bingos)
      score = (num_bingos, hits)
      if score > hi_score:
        hi_score = score
        print('New high score: {1} items forming {0} bingos'.format(*hi_score))
        print('Seed:', seed)
      outq.put((len(itemList), -num_bingos, -hits, seed, board))

  def NewCard(self):
    global hi_seed
    hi_seed += 1
    myseed = str(hi_seed)
    board = list(genCardArray(myseed))
    return (0, 0, 0, myseed, board)


WIDTH = 256


class ARC4(object):
  def __init__(self, key):
    if not key:
      key = [0]
    j = 0
    self.s = list(range(WIDTH))
    for i in range(WIDTH):
      t = self.s[i]
      j = int(j + key[i % len(key)] + self.s[i]) % WIDTH
      self.s[i] = self.s[j]
      self.s[j] = t
    self.i = 0
    self.j = 0
    self.g(WIDTH)  # RC4-drop[256]: Drop the first 256 values.

  def g(self, count):
    t = 0
    r = 0.0
    i = self.i
    j = self.j
    s = self.s
    for _ in range(count):
      i += 1
      i %= WIDTH
      t = s[i]
      j += t
      j %= WIDTH
      s[i] = s[j]
      s[j] = t
      r = r * WIDTH + s[(s[i] + s[j]) % WIDTH]
    self.i = i
    self.j = j
    return r


class PRNG(object):
  def __init__(self, key):
    self.arc4 = ARC4(key)

  def int32(self):
    return self.arc4.g(4)

  def double(self):
    n = self.arc4.g(6)
    d = WIDTH**6
    x = 0
    sig = 2**52
    overflow = 2**53

    while n < sig:
      n = (n + x) * WIDTH
      d *= WIDTH
      x = self.arc4.g(1)
    while n >= overflow:
      n //= 2
      d //= 2
      x = int(x) >> 1
      x &= 0b01111111
    return (n + x) / d


def refresh():
  items = json.loads(
      requests.get('http://kinda.sexy/trev/bingo/items.json').text)
  for item in items:
    add(item)


if __name__ == '__main__':
  workers = [Worker() for _ in range(1)]
  for worker in workers:
    worker.daemon = True
    worker.start()
  refresh()
  import IPython
  IPython.embed()
