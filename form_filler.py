def ask_for_field(field):

    label = field["label"]

    answer = input(
        f"\nEnter {label}: "
    )

    return answer.strip()


def collect_form_data(fields):

    data = {}

    print("\n=== FORM FILLING ===")

    for field in fields:

        key = field["label"]

        value = ask_for_field(field)

        data[key] = value

    return data


def generate_draft(form_data):

    lines = []

    lines.append(
        "=== COMPLETED FORM DRAFT ==="
    )

    lines.append("")

    for field, value in form_data.items():

        lines.append(
            f"{field}: {value}"
        )

    lines.append("")

    lines.append(
        "Please review the information "
        "before submission."
    )

    return "\n".join(lines)


if __name__ == "__main__":

    fields = [
        {
            "label": "Applicant Name",
            "type": "text"
        },
        {
            "label": "Address",
            "type": "text"
        },
        {
            "label": "Mobile Number",
            "type": "text"
        }
    ]

    data = collect_form_data(fields)

    print(
        generate_draft(data)
    )