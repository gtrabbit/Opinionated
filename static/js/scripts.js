const deleteCategory = function(url){
	if (window.confirm('Really delete this category? This will also delete all associated opinions')){
		let xhr = new XMLHttpRequest()
		xhr.open('DELETE', url)
		xhr.send(null)
		xhr.onreadystatechange = function(){
			if (xhr.readyState === 4){
				if (xhr.status === 200){
					window.location.reload()
				} else {
					console.log(xhr.responseText)
				}			
			} 
		}
	}
}

const deleteUser = function(url){
		if (window.confirm('Really delete this account? This will also delete all associated categories and opinions')){
		let xhr = new XMLHttpRequest()
		xhr.open('DELETE', url)
		xhr.send(null)
		xhr.onreadystatechange = function(){
			if (xhr.readyState === 4){
				if (xhr.status === 200){
					window.location.href = '/'
				} else {
					console.log(xhr.responseText)
				}			
			} 
		}
	}
}