addEventListener("DOMContentLoaded", function()
{
	var elements = document.getElementsByClassName("audio-sample");
	for (var i = 0; i < elements.length; i++)
	{
		var element = elements[i];
		element.id = "audio-sample" + i;
		
		var button = document.createElement("a");
		button.href = "javascript:document.getElementById(\"" + element.id + "\").play(); void(0);";
		button.textContent = "🔊";
		button.tabIndex = 0;
		button.ariaLabel = "Play Button";
		element.after(button);
	}
});