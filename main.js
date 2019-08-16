
var entities;
var text = "";
var current_ent = -1;

$(document).ready (  () => {
    $("body").mouseup( () => {
        var selection = window.getSelection();
        var selectionStr = selection.toString()
        if (selectionStr.length > 0) {
            var range = selection.getRangeAt(0)
            console.log(range)
            console.log(selectionStr)
        }
    })

    getText();
    getEntities();
})

initializeListeners = () => {
    saveEntity();
    skipEntity();
    updateEntityLabel();
    setPreviousEntity();
    saveToDisk();
}

setPreviousEntity = () => {
    $("#back-button").click(() => {
        if (current_ent > 0) {
            current_ent--;
            $("#entity-text").text(entities[current_ent].name)
            highlightEntityInText();
        }
    })
}

highlightEntityInText = () => {
    $("#text").text(text)

    var entity = $("#text").text().substring(entities[current_ent].start, entities[current_ent].end)

    console.log(entity)

    $("#text").html($("#text").text().replace(entity, "<span class=\"highlight\">" + entity + "</span>"))
}

setNextEntity = () => {
    if (current_ent < entities.length-1) {
        current_ent++;
        $("#entity-spinner").hide()
        $("#entity-text").text(entities[current_ent].name)
        highlightEntityInText();
    }

    // TODO: auto select the label guessed by SpaCy
    // $('#label-select option[value="' + entities[current_ent].label + '"]').prop('selected', true)
}

saveEntity = () => {
    $("#next-button").click( () => {
        console.log("Saving entity...");
        var search_url = "/saveEntity?label=" + entities[current_ent].label +  "&start=" + entities[current_ent].start + "&end=" + entities[current_ent].end
        $.ajax({
            url: search_url,
            context: document.body
          }).done(function(data) {
            entitySet = JSON.parse(data)
            console.log("Entity set after saving:")
            console.log(entitySet)
            setNextEntity()
        });
    })
}

getEntities = () => {
    console.log("Getting entities data...");
    var search_url = "/getEntities"

    $.ajax({
        url: search_url,
        context: document.body
      }).done(function(data) {
        entities = JSON.parse(data)
        console.log(entities)
        setNextEntity();
        initializeListeners();
    });
}

getText = () => {
    console.log("Getting text data...");
    var search_url = "/getText"
    $.ajax({
        url: search_url,
        context: document.body
      }).done(function(data) {
        $("#text").text(data)
        text = data
    });
}

updateEntityLabel = () => {
    $("#label-select").change( () => {
        console.log("Updating label to " + $("#label-select").val())
        entities[current_ent].label = $("#label-select").val()
    })
}

skipEntity = () => {
    $("#skip-button").click( () => {
        console.log("Skipping entity... ");
        setNextEntity();
    })
}

saveToDisk = () => {
    $("#save-button").click( () => {
        console.log("Saving to disks... ")
        var search_url = "/saveToDisk"
        $.ajax({
            url: search_url,
            context: document.body
          }).done(function(data) {
            console.log(data)
        });
    })
}

