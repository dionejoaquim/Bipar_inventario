[app]

title = Bipar Inventario
package.name = biparinventario
package.domain = com.vylor

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt

version = 1.0

requirements = python3,kivy==2.3.1,python-tds

orientation = portrait

android.permissions = INTERNET

fullscreen = 0

android.api = 34
android.minapi = 21
android.archs = arm64-v8a,armeabi-v7a

android.entrypoint = org.kivy.android.PythonActivity

exclude_exts = spec,pyc,pyo

log_level = 2
warn_on_root = 1
