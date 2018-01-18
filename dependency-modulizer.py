import os, sys, time, subprocess, zipfile, shutil, json, urllib2
from xml.etree import ElementTree as et

ERROR_STR= """Error removing %(path)s, %(error)s """

def cleanup():
	shutil.rmtree("temp/")
	os.remove("module-info.java")

def zipdir(path, ziph):
	# ziph is zipfile handle
	for root, dirs, files in os.walk(path):
		for file in files:
			if ".jar" in file:
				continue;
			ziph.write(os.path.join(root, file))

if len(sys.argv) != 3:
	print "Not enough arguments."
	print sys.argv[0] + " [jar] [Should overwrite existing jar(y/n)]"
	sys.exit()

jar = sys.argv[1]

# unpack jar
print "Unpacking jar " + jar
zf = zipfile.ZipFile(jar)
zf.extractall(path = "temp" + os.sep + "original")
zf.close()

# Read maven dependecy information from unpacked jar
folder = ""
for root, dirs, files in os.walk("temp" + os.sep + "original" + os.sep + "META-INF" + os.sep + "maven" + os.sep):
	for file in files:
		if file.endswith(".xml"):
			folder = os.path.join(root, file)
			print "Reading pom.xml (" + folder + ")"
			if folder == "":
				print "Maven dependency file not found."
				sys.exit()

ns = "http://maven.apache.org/POM/4.0.0"
group_id = artifact_id = version = ""
tree = et.ElementTree()
tree.parse(folder)
p = tree.getroot().find("{%s}parent" % ns)
if p is not None:
	if p.find("{%s}groupId" % ns) is not None:
		group_id = p.find("{%s}groupId" % ns).text
	if p.find("{%s}version" % ns) is not None:
		version = p.find("{%s}version" % ns).text
	if tree.getroot().find("{%s}groupId" % ns) is not None:
		group_id = tree.getroot().find("{%s}groupId" % ns).text
	if tree.getroot().find("{%s}artifactId" % ns) is not None:
		artifact_id = tree.getroot().find("{%s}artifactId" % ns).text
	if tree.getroot().find("{%s}version" % ns) is not None:
		version = tree.getroot().find("{%s}version" % ns).text

print "Artifact information:"
print "Group ID: " + group_id
print "Artifact ID: " + artifact_id
print "Version: " + version

# Get module information from java
print "Getting automatics module information from the current jar file " +jar
command = subprocess.check_output('jar --file ' + jar + ' --describe-module')
java_command = command.split("\n")

module_info = []

for java_command_line in java_command:
	if java_command_line == "":
		continue;
	if java_command_line == "\r":
		continue;
	module_info.append(java_command_line)

# This is the code holding the java code (module-info.class)
print "Creating the module-information file for " + jar
module_info_java_code = ""

# Parse the module_info and write it to the module_info_java_code
module_name = module_info[1].split("@")
module_info_java_code = "module " + module_name[0] + " {\n"

# Remove used elements from list.
# Note: purposely dublicated lines.
module_info.pop(0)
module_info.pop(0)

for module_info_line in module_info:
	module_requirements = module_info_line.split(" ")
	keyword = module_requirements[0]
	value = module_requirements[1]
	# replace contain with exports
	if keyword == "contains":
		keyword = "exports"
	module_info_java_code = module_info_java_code + keyword + " " + value + ";\n"
module_info_java_code = module_info_java_code + "}"

jf = open("module-info.java", "wb")
jf.write(module_info_java_code)
jf.close()

print "Module information file created."
print "Compiling module information file"

# Compile the module file.
compile_information = subprocess.check_output('javac -d temp'+os.sep+'original'+os.sep+' module-info.java')

if os.path.isfile("temp"+os.sep+"original"+os.sep+"module-info.class"):
	print "Module information file successfully compiled"
else:
	print "Module information file couldn't be compiled."
	print compile_information
	print ""
	print "Please try to fix these errors and try to run this tool again."
	cleanup()
	sys.exit()

old_working_dir = os.getcwd()
os.chdir("temp"+os.sep+"original"+os.sep)

print "Packing the modular jar"

modular_jar = ""
if len(sys.argv) == 4:
	modular_jar = sys.argv[3] + "-" + version + ".jar"
else:
	modular_jar = "x "+jar

zipf = zipfile.ZipFile(modular_jar, 'w', zipfile.ZIP_DEFLATED, allowZip64 = True)
zipdir(".", zipf)
zipf.close()

print "Packaged modular jar in " + modular_jar

os.chdir(old_working_dir)
print "Done"
if sys.argv[2] == "y":
	print "Replacing " + jar + " with modulized jar " + modular_jar
	shutil.copyfile("temp"+os.sep+"original"+os.sep+modular_jar, jar)
else:
	print "Modular jar placed in " + modular_jar
	shutil.copy("temp"+os.sep+"original"+os.sep+modular_jar, ".")

cleanup()
