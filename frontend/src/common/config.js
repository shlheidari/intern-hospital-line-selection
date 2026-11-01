/** Reads the JSON the server embedded with Django's `json_script`. */
export function readConfig(id = 'page-config') {
  return JSON.parse(document.getElementById(id).textContent);
}
