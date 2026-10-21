import './style.css'

const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const statusContainer = document.getElementById('statusContainer');
const resultsContainer = document.getElementById('resultsContainer');
const statusText = document.getElementById('statusText');
const badgeCache = document.getElementById('badgeCache');
const badgeSearching = "px-2.5 py-0.5 rounded text-xs font-semibold bg-black text-white border border-grey-100";
let currentPage = 1;
const itemsPerPage = 10;
const processing = "⚙️ Processing . . .";
const servedFromCache = "🗄️ Hit: Served from Redis Cache";
const servedFromBackend = "🗄️ Miss: Served from backend";
const error = "❌ Error: Something went wrong";
const paginationContainer = document.getElementById('paginationContainer');
let currentFilteredResults = []; // Store the filtered results for pagination

//SearchOperation function
async function performSearchOperation() {
  const query = searchInput.value.trim();
  let tries = 0;
  const maxTries = 15;

  if (query === '' || query.length === 0 || query === ' '){
    alert('Empty query. Please enter a valid search term.');
    return;
  }

  console.log("searching for: " + query);
  statusContainer.classList.remove('hidden');
  statusText.textContent = 'Consulting the API for ' + query + '...';
  badgeCache.className = badgeSearching;
  badgeCache.textContent = processing;
  let reachedBackend = false;
  
  let jsonData = null;

  // calling the C# API endpoint
  try {
    while (tries < maxTries)
    {
      tries++;
      let response = await fetch('http://localhost:5000/api/search?q='+ encodeURIComponent(query));
      
      if(response.status === 202) {
        let pendingData = await response.json();
        reachedBackend = true;
      }
      else if(response.status === 200) {
        
        jsonData = await response.json();
        console.log("Data received", jsonData);
        statusText.textContent = 'Results served';

        if(reachedBackend) 
          {
          badgeCache.textContent = servedFromBackend;
        }
        else
        {
          badgeCache.textContent = servedFromCache;
        }
        break;
      }
      else
        throw new Error('There was a problem with the fetch operation: ' + response.statusText);

      console.log("Waiting for the server to finish processing...");
      
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    if (tries >= maxTries) 
    {
      throw new Error('Max tries exceeded while waiting for the server to finish processing.');
    }
    // 3. Convertimos la respuesta a formato JSON para poder usarla en JS
    currentFilteredResults = [];
    currentFilteredResults = jsonData.filteredResults;
    // console.log(jsonData.filteredResults);
    resultsContainer.innerHTML = `<h1>Results for: ${query}</h1>`;
    generatePaginationControls(currentFilteredResults.length, itemsPerPage);
    UpdatePageDataAndControls(1);
  } catch (error) {
    // If the server is down or there is a network error, we catch it here
    console.error("There was an error in the network request:", error);
    statusText.textContent = error;
  }

}

//Generates Pagination based on the number of results and items per page
function generatePaginationControls(totalItems, currentPage) {
  paginationContainer.innerHTML = '';
  const totalPages = Math.ceil(totalItems / itemsPerPage);

  for (let i = 1; i <= totalPages; i++) {
    const button = document.createElement('button');
    button.className = `px-3 py-1 m-1 border rounded cursor-pointer ${i === currentPage ? 'bg-blue-500 text-white font-bold' : 'bg-gray-200 hover:bg-gray-300'}`;
    button.textContent = i;

    button.addEventListener('click', () => {
      UpdatePageDataAndControls(i);
      generatePaginationControls(totalItems, i);
    });

    paginationContainer.appendChild(button);
  }
}

// Update the displayed results and pagination controls based on the current page
function UpdatePageDataAndControls(currentPage) {
  resultsContainer.innerHTML = ''; // Clear previous results
      console.log(currentFilteredResults);
      let sublist = currentFilteredResults.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);
      console.log("Displaying results for page " + currentPage + ": ", sublist);
      for (let i = 0; i < sublist.length; i++) {
        let result = sublist[i];
        let desc = result.metadata.description;
        let shoretenedTitle = result.metadata.title.length > 100 ? result.metadata.title.substring(0, 100) + "..." : result.metadata.title;

        if (desc === "No description found")
          desc = result.metadata.title;

        resultsContainer.innerHTML += `
      <div class="flex flex-col gap-2 p-4 border border-gray-300 rounded-lg hover:bg-gray-50 transition duration-300">
        <a href="${result.url}" target="_blank" class="text-lg font-semibold text-blue-600 hover:underline">
          ${shoretenedTitle}
        </a>
        <p class="text-sm text-gray-600"> ${desc} </p>
      </div>
      `;
      }
}

//Registering event listener for the search button
searchButton.addEventListener('click', performSearchOperation);

searchInput.addEventListener('keypress', function(event) {
  if (event.key === 'Enter') {
    performSearchOperation();
  }
});

console.log("¡Search application initialized!");