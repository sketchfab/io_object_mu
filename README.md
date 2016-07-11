io_object_mu
==========

Blender addon for importing and exporting KSP .mu files.

NOTE: the import/export functionality is still under heavy development, but
importing is mostly working for static meshes (minus normals and tangents).

mu.py is the main workhorse: it reads and writes .mu files. It is independent
of blender and works with both versions 2 and 3 of python. Some notes on mu.py:
* vectors and quaternions are converted from Unities LHS to Blender's RHS on
load and back again when writing.
* vertex tangents are broken (they are incorrectly treated as quaternions), but
will be preserved if mu.py is used to copy a .mu file. This is a bug.
* mu.py always writes version 2 .mu files.
* it may still break, back up your work.


craft file parsing
==================

Craft are now supported by the plugin.
A .craft file is used to define an entire spaceship, by referencing all its parts
and giving the required data to assemble them, locate and orient them, and also
all the dynamics/module parts for the game.

The entry of the plugin is in the *__main__.py* file, that can accept a single .mu part,
or a craft file in input.

Note that the craft file must be given with all the required parts (with the good paths) in order
to get the good output.

Example:
```
blender -b -P io_object_mu/__main__.py -- -i sample.craft -o craft.blend
```