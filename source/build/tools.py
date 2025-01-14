# -*- coding: utf-8 -*-

import subprocess
import glob
import string
import os
import shutil
import random
import json


def getVersion(pathCompatible):
    version = subprocess.check_output(
        ["git", "describe", "--tags", "--always", "--match", "v[0-9]*"]).strip()
    version = version.decode('utf-8')
    changes = subprocess.check_output(["git", "status", "--porcelain"]).strip()
    changes = changes.decode('utf-8')

    if len(changes) > 0:
        version = version+'-*'

    if pathCompatible:
        version = version.replace("*", "#")
        version = version.replace(":", "#")
        version = version.replace("?", "#")
        version = version.replace("|", "#")
        version = version.replace("/", "#")
        version = version.replace("\\", "#")

    return version


def checkFlags(withWiFi, withPipedream, withSettings, colorset):
    if isinstance(withWiFi, bool) and withWiFi == True:
        raise Exception("withWiFi only False or integer is valid")
    elif isinstance(withWiFi, bool) and withWiFi == False:
        pass
    elif not isinstance(withWiFi, int) or withWiFi < 0 or withWiFi > 9:
        raise Exception("withWiFi invalid value: {}".format(withWiFi))

    if not isinstance(withPipedream, bool):
        raise Exception("withPipedream only True, False is valid")

    if not isinstance(withSettings, bool):
        raise Exception("withSettings only True, False is valid")

    if not isinstance(colorset, int) or (colorset != 0 and colorset != 1):
        raise Exception("colorset only 0, 1 is valid")


def writePreHeader(env):
    f = open(env["PROJECT_SRC_DIR"] + "/pre.h", "w")
    letters = string.ascii_lowercase
    f.write('#pragma once\n')
    f.write('#define SECRET_AP_PASSWORD F("%s")\n' %
            (''.join(random.choice(letters) for i in range(8))))
    f.write('#define VERSION F("%s")\n' % (getVersion(False)))
    f.close()


def writeSpiffsVersion(env):
    f = open(env["PROJECT_DATA_DIR"] + "/spiffs.version", "w")
    f.write('%s' % (getVersion(False)))
    f.close()
    shutil.copyfile(env["PROJECT_DATA_DIR"] + "/spiffs.version",
                    env["PROJECT_DATA_DIR"] + "/settings.version")
    shutil.copyfile(env["PROJECT_DATA_DIR"] + "/spiffs.version",
                    env["PROJECT_DATA_DIR"] + "/about.version")
    shutil.copyfile(env["PROJECT_DATA_DIR"] + "/spiffs.version",
                    env["PROJECT_DATA_DIR"] + "/admin.version")


def removeBuildBinFiles(env):
    try:
        os.remove(env["PROJECT_BUILD_DIR"] + "/" +
                  env["PIOENV"] + "/spiffs.bin")
    except OSError:
        pass
    try:
        os.remove(env["PROJECT_BUILD_DIR"] + "/" +
                  env["PIOENV"] + "/firmware.bin")
    except OSError:
        pass


def getAssetsDirectoryName(env, withWiFi, withPipedream, withSettings):
    version = getVersion(True)
    path = "assets/" + version + "/[" + env["PIOENV"] + "]"

    if not isinstance(withWiFi, bool):
        path += "_wifi[" + str(withWiFi) + "]"
    if withPipedream:
        path += "_pipedream"
    if withSettings:
        path += "_settings"

    path += "/"
    return path


def getFirmwareFilename():
    version = getVersion(True)
    return "cointhing_" + version + ".bin"


def getSpiffsFilename():
    version = getVersion(True)
    return "spiffs_" + version + ".bin"


def getUploadScriptFilename(sh):
    version = getVersion(True)
    name = "cointhing_upload_" + version
    if sh:
        name += ".sh"
    else:
        name += ".bat"
    return name


def createAssetsDirectory(env, withWiFi, withPipedream, withSettings):
    path = getAssetsDirectoryName(env, withWiFi, withPipedream, withSettings)
    try:
        os.makedirs(path)
    except:
        pass
    return path


def createUploadScript(env, withWiFi, withPipedream, withSettings):
    assets = getAssetsDirectoryName(env, withWiFi, withPipedream, withSettings)
    filename = assets + "/" + getUploadScriptFilename(False)
    firmware = getFirmwareFilename()
    spiffs = getSpiffsFilename()

    f = open(filename, "w")
    f.write("python -m esptool erase_flash\n")
    f.write(
        "python -m esptool --before default_reset --after hard_reset --chip esp8266 --baud 921600 write_flash 0x0 .\{0} 0x200000 .\{1} \n\n".format(firmware, spiffs))
    f.write("pio device monitor -b 115200\n")
    f.close()

    filename = assets + "/" + getUploadScriptFilename(True)

    f = open(filename, "w")
    f.write("export PATH={0}\n".format(env["ENV"]["Path"]))
    f.write("python -m esptool erase_flash\n".format(env["PYTHONEXE"]))
    f.write(
        "python -m esptool --before default_reset --after hard_reset --chip esp8266 --baud 921600 write_flash 0x0 .\{0} 0x200000 .\{1} \n\n".format(firmware, spiffs))
    f.write("pio device monitor -b 115200\n")
    f.close()
    os.chmod(filename, 0o777)


def copyFirmware(env, withWiFi, withPipedream, withSettings):
    assets = getAssetsDirectoryName(env, withWiFi, withPipedream, withSettings)

    shutil.copyfile(env["PROJECT_BUILD_DIR"] + "/" + env["PIOENV"] +
                    "/firmware.bin", assets + "/" + getFirmwareFilename())


def copySpiffs(env, withWiFi, withPipedream, withSettings):
    assets = getAssetsDirectoryName(env, withWiFi, withPipedream, withSettings)

    shutil.copyfile(env["PROJECT_BUILD_DIR"] + "/" + env["PIOENV"] +
                    "/spiffs.bin", assets + "/" + getSpiffsFilename())


def prepareSecretFiles(env, withWiFi, withPipedream, withSettings, colorset):
    assets = getAssetsDirectoryName(env, withWiFi, withPipedream, withSettings)
    try:
        os.remove(env["PROJECT_DATA_DIR"] + "/secrets.json")
    except OSError:
        pass

    try:
        os.remove(env["PROJECT_DATA_DIR"] + "/settings.json")
    except OSError:
        pass

    with open("secrets/secrets.json", "r") as f:
        secrets = json.load(f)

    if not isinstance(withWiFi, bool):
        secrets["ssid"] = secrets["ssids"][withWiFi]
        secrets["pwd"] = secrets["pwds"][withWiFi]

    secrets.pop("ssids", None)
    secrets.pop("pwds", None)

    if not withPipedream:
        secrets.pop("pipedream", None)

    with open(env["PROJECT_DATA_DIR"] + "/secrets.json", "w") as f:
        json.dump(secrets, f, indent=2, separators=(',', ':'))

    shutil.copyfile(env["PROJECT_DATA_DIR"] +
                    "/secrets.json", assets + "/secrets.json")

    # settings.json only if avaiable
    if withSettings:
        try:
            shutil.copyfile("secrets/settings.json",
                            env["PROJECT_DATA_DIR"] + "/settings.json")
            shutil.copyfile("secrets/settings.json", assets + "/settings.json")
        except OSError:
            pass

    with open(env["PROJECT_DATA_DIR"] + "/colorset", "w") as f:
        f.write(str(colorset))
    shutil.copyfile(env["PROJECT_DATA_DIR"] +
                    "/colorset", assets + "/colorset")


def prepareHTMLFiles(env):
    fileList = glob.glob(env["PROJECT_DATA_DIR"] + "/*.gz")
    for filePath in fileList:
        try:
            os.remove(filePath)
        except OSError:
            print("Error while deleting file")

    # Add ./source/build to PATH for windows to execute gzip
    subprocess.call(
        ["gzip", "-k", "-f", env["PROJECT_DATA_DIR"] + "/../html/settings.html"])
    subprocess.call(
        ["gzip", "-k", "-f", env["PROJECT_DATA_DIR"] + "/../html/about.html"])
    subprocess.call(
        ["gzip", "-k", "-f", env["PROJECT_DATA_DIR"] + "/../html/admin.html"])
    subprocess.call(
        ["gzip", "-k", "-f", env["PROJECT_DATA_DIR"] + "/../html/style.css"])

    os.replace(env["PROJECT_DATA_DIR"] + "/../html/settings.html.gz",
               env["PROJECT_DATA_DIR"] + "/settings.html.gz")
    os.replace(env["PROJECT_DATA_DIR"] + "/../html/about.html.gz",
               env["PROJECT_DATA_DIR"] + "/about.html.gz")
    os.replace(env["PROJECT_DATA_DIR"] + "/../html/admin.html.gz",
               env["PROJECT_DATA_DIR"] + "/admin.html.gz")
    os.replace(env["PROJECT_DATA_DIR"] + "/../html/style.css.gz",
               env["PROJECT_DATA_DIR"] + "/style.css.gz")


def copyHTMLFiles(env, withWiFi, withPipedream, withSettings):
    assets = getAssetsDirectoryName(env, withWiFi, withPipedream, withSettings)

    shutil.copyfile(env["PROJECT_DATA_DIR"] +
                    "/settings.html.gz", assets + "/settings.html.gz")
    shutil.copyfile(env["PROJECT_DATA_DIR"] +
                    "/about.html.gz", assets + "/about.html.gz")
    shutil.copyfile(env["PROJECT_DATA_DIR"] +
                    "/admin.html.gz", assets + "/admin.html.gz")

    shutil.copyfile(env["PROJECT_DATA_DIR"] +
                    "/settings.version", assets + "/settings.version")
    shutil.copyfile(env["PROJECT_DATA_DIR"] +
                    "/about.version", assets + "/about.version")
    shutil.copyfile(env["PROJECT_DATA_DIR"] +
                    "/admin.version", assets + "/admin.version")
