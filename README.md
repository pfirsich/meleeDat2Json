# meleeDat2Json
meleeData2Json is a program to dump character data files from Super Smash Bros. Melee to JSON. This data includes [Attributes (some)](http://opensa.dantarion.com/wiki/Attributes_(Melee)) and Subactions, which are "scripts" that exist for each character state. They are comprised of "Events"/"Commands", which are also parsed by meleeDat2Json, including their parameters.

meleeDat2Json aims to make character/move data directly and easily accessible for inclusion in websites or whatever other clever ideas other people might have and also tries to serve as a reference implementation for parsing character .dat files and a reference for the subaction commands that have already been understood. If you notice things I could improve in that regard (i.e. make the file parsing more robust, parse more information or add more commands), please let me know (via issue tracker) or make a pull request!

## .dat dumps
meleeDat2Json does not have many options that significantly alter the output, so most people will probably not require to execute it themselves. I uploaded JSON dumps of the character files here:

[Melee Files/dat-dumps](http://melee.theshoemaker.de/?dir=dat-dumps)

Embedded in the character files are also the animation files, which I dumped as well to [dat-dumps/animation-files](http://melee.theshoemaker.de/?dir=animation-files) in case anyone needs them.

## meleeFrameDataExtractor
The initial motivation and my main project utilizing meleeDat2Json is [meleeFrameDataExtractor](https://github.com/pfirsich/meleeFrameDataExtractor), which extracts frame data, like it is provided in numerous threads on [smashboards](https://smashboards.com/), [Smash Wiki](https://www.ssbwiki.com/) or on [superdoodleman's website](http://www.angelfire.com/games5/superdoodleman/frames.html) directly from the character files and in a format more easily accessible in other projects, like my framedata website [melee-framedata](http://melee-framedata.theshoemaker.de/).

## Usage
If you have some reason to execute meleeDat2Json yourself, you need to install Python 3, then just navigate to the repository root and call `pip install .`.
Then you can just call:
```console
meleedat2json --help
```
to view help on the command line options. If the help is not sufficient, please open an issue and let me know what to improve!
