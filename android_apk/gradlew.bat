@rem
@rem Copyright 2015 the original author or authors.
@rem Licensed under the Apache License, Version 2.0
@rem

@if "%DEBUG%"=="" @echo off

set DIRNAME=%~dp0
if "%DIRNAME%"=="" set DIRNAME=.

@rem Find java.exe
set JAVA_EXE=java.exe

if defined JAVA_HOME goto findJavaFromJavaHome
goto execute

:findJavaFromJavaHome
set JAVA_HOME=%JAVA_HOME:"=%
set JAVA_EXE=%JAVA_HOME%/bin/java.exe

if exist "%JAVA_EXE%" goto execute
echo ERROR: JAVA_HOME is set to an invalid directory: %JAVA_HOME%
exit /b 1

:execute
@rem Setup the command line
set CLASSPATH=%DIRNAME%\gradle\wrapper\gradle-wrapper.jar

@rem Execute Gradle
"%JAVA_EXE%" %DEFAULT_JVM_OPTS% %JAVA_OPTS% %GRADLE_OPTS% ^
  "-Dorg.gradle.appname=%APP_BASE_NAME%" ^
  -classpath "%CLASSPATH%" ^
  org.gradle.wrapper.GradleWrapperMain %*
