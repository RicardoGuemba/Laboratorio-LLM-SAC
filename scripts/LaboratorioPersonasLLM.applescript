on run
    set appPath to POSIX path of (path to me as alias)
    set projectRoot to do shell script "dirname " & quoted form of appPath
    set launcher to projectRoot & "/Laboratorio-Personas-LLM.app/Contents/MacOS/launcher"

    try
        do shell script "export PATH=/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin; " & quoted form of launcher
        display notification "Laboratório aberto no navegador!" with title "Laboratório Personas LLM"
    on error errMsg number errNum
        set logHint to projectRoot & "/.lab-personas-llm-launcher.log"
        display dialog "Não foi possível iniciar o Laboratório Personas LLM." & return & return & errMsg & return & return & "Detalhes em:" & return & logHint buttons {"OK"} default button "OK" with icon stop
    end try
end run
