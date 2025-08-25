package common

import (
	"encoding/csv"
	"io"
	"os"
	"strconv"
)

const NOMBRE_CSV = 0
const APELLIDO_CSV = 1
const DNI_CSV = 2
const FECHA_CSV = 3
const NUMERO_CSV = 4

func LoadBatches(id string, batch_size int, client *Client) {

	file, err := os.Open("./agency.csv")
	if err != nil {
		log.Criticalf("%s", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	bets, err := GetBatch(batch_size, reader)
	for ; err == nil && len(bets) > 0; bets, err = GetBatch(batch_size, reader) {
		client.MakeBets(bets)
	}
	if err != io.EOF {
		log.Criticalf("action: parse_bet | result: fail | client_id: %v | error: %v",
			id,
			err,
		)
	}
}

func GetBatch(batch_size int, reader *csv.Reader) ([]Bet, error) {
	bets := make([]Bet, 0, batch_size)
	for len(bets) < batch_size {
		record, err := reader.Read()
		if err != nil {
			if err == io.EOF {
				return bets, nil
			}
			return nil, err
		}

		dni, err := strconv.ParseInt(record[DNI_CSV], 10, 32)
		if err != nil {
			return nil, err
		}

		number, err := strconv.ParseInt(record[NUMERO_CSV], 10, 32)
		if err != nil {
			return nil, err
		}

		bet := Bet{
			Name:    record[NOMBRE_CSV],
			Surname: record[APELLIDO_CSV],
			Dni:     uint32(dni),
			Birth:   record[FECHA_CSV],
			Number:  uint32(number),
		}

		bets = append(bets, bet)
	}
	return bets, nil
}
