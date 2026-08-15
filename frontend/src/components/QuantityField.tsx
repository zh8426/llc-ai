type QuantityFieldProps = {
  label: string
  unit: string
  value: string
  onChange: (value: string) => void
  disabled: boolean
}

export default function QuantityField({
  label,
  unit,
  value,
  onChange,
  disabled,
}: QuantityFieldProps) {
  return (
    <label className="field">
      <span>{label}</span>
      <div className="input-with-unit">
        <input
          type="number"
          step="any"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
        />
        <small>{unit}</small>
      </div>
    </label>
  )
}
