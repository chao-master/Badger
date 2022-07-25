# Badger

Cool badgers badges, my over engineered solution for showing images on an eink
display around my neck

## What's here?
The App system, plus other things I run off my badger. The app system is my attempt to make a system for handling button presses, updates, and other important things (like screens) on the badger, in
order to make developing on it easier and make less use of global variables and methods.
What can I say, 5 years of professional object oriented coding has made me a bit object mad.

The architecture might by no means be perfect, but this is after 3 or so iterations of it, so I'm happy with where it is now.

## How stable is it?

Not at all!  
All changes may be breaking at this point, we're in the go fast and break stuff stage of development, and I did mostly upload this to show my friends. I'll try to be a good little kitty and document any breaking changes I make each commit, but I'm not running rigirous tests aganist old versions here!

## How do I use the badge!
If you're just here for the badge:

 1. Copy `App.py` and `badge.py` to your badger
    1. Edit `badge.py` changing `#Configurable constants` at the top to customizes the name and qr code link
 2. Create a folder in the badger called `badges`
 3. Inside the `badges` folder make a file called `pronouns.txt`
    1. Inside this file add the pronouns you want to be able to choose from, one per line
 4. Inside the `badges` folder make a file called `bylines.txt`
    1. Inside this file add descriptions about yourself that you want to be able to choose from one per line
 5. Inside the `badges` folder create two new folders `images` and `halfImages`
    1. Collect some 128x128 images you wanna show
    2. Convert them to `.bin` files
    3. Upload these to `badges/images`
    4. Create a half size 64x64 copy for each image
    5. Covert them to `.bin` files
    6. Upload these to `badges/halfImages`

You can now run the badge by selecting badge from the badger start menu, when running:

 * `A` opens the avatar selector
   * Use `up` and `down` to select a different avatar
   * `A` to cancel
   * `B` to go forward one page
   * `C` to use the selected avatar
 * `B` opens the pronoun selector and `C` opens the about line selector
   * Use `up` and `down` to select a different pronouns/about lines
   * `A` to cancel
   * `B` to use the currently selector pronoun/about line, keep pressing until it's in the slot you want
   * `C` to confirm and use the selected lines
 * `down` swaps between your avatar and a QR code, this is still a work in progress

I was going to use the user button to lock it, but the cool thing about the badger, you can lock the screen just by turning the battery pack off!
