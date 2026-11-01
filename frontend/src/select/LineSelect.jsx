export const PROMPT = 'لطفا لاین مورد نظر را انتخاب کنید';

/** Drop-down with the lines that still have a free seat. */
export default function LineSelect({ lines, value, onChange }) {
  return (
    <div id="select_line">
      <select value={value || PROMPT} onChange={(event) => onChange(event.target.value)}>
        {[PROMPT, ...lines].map((option) => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
    </div>
  );
}
